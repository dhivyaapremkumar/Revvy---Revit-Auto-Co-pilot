"""Structured Revit tools: fixed, pre-tested operations instead of asking the
LLM to hand-write IronPython through execute_revit_code on every call.

Every wall-creation failure this project has hit so far (wrong Name-lookup
pattern, ElementId.IntegerValue no longer existing, wall-type/level names
that don't match the actual model, output-length truncation on longer
scripts) came from the same root cause: execute_revit_code makes the LLM
generate code from scratch each time, blind to the model's actual state,
with nothing validating the result before it's committed. These tools wrap
execute_revit_code with fixed snippets (baked-in, already-correct Revit
2027 API patterns) and a resolve-before-create step for names, so the LLM
calls a well-defined function instead of writing Revit API code.
"""
from __future__ import annotations

import json

from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel


class RoomSpec(BaseModel):
    """One room in a create_floor_plan() batch -- an axis-aligned rectangle."""

    name: str
    x: float  # southwest/bottom-left corner
    y: float
    width_ft: float  # extends in +x
    depth_ft: float  # extends in +y
    number: str | None = None

# execute_revit_code (RevitMCP.extension/tools/code_execution_tools.py) returns
# EITHER the executed script's print() output (success) OR a human-readable
# "=== ERROR DETAILS ===" block with a traceback (failure) -- see
# RevitMCP.extension/tools/utils.py's format_response(). Every snippet below
# prints exactly one JSON value, so success/failure can be told apart cleanly.
_ERROR_PREFIX = "=== ERROR DETAILS ==="

# The only Name-lookup pattern confirmed (via direct live testing against this
# project's Revit 2027 model) to work on BOTH instance elements (e.g. Level)
# and type elements (e.g. WallType) -- see realtime_session.py's _INSTRUCTIONS
# for the full story of why the two more "obvious" patterns each silently
# fail on one kind of element or the other.
_NAME_EXPR = "DB.Element.Name.__get__({0})"

# Constructing DB.ElementId(some_int) directly is ambiguous in this Revit
# version -- confirmed twice already this session (wall cleanup scripts,
# PropertyLine.Create's IList resolution) with "Multiple targets could
# match: ElementId(BuiltInParameter), ElementId(BuiltInCategory),
# ElementId(Int64))". Every generic (any-element-type) tool below resolves
# an id string by collecting ALL non-type elements and matching str(Id)
# instead, the same workaround used everywhere else this session.
_FIND_ELEMENT = (
    "elems = DB.FilteredElementCollector(doc).WhereElementIsNotElementType().ToElements()\n"
    "el = next((e for e in elems if str(e.Id) == {element_id!r}), None)\n"
)


def _extract_text(result: object) -> str:
    """MCP tools return a list of content blocks (`[{"type": "text", "text": "..."}]`)
    via ainvoke, not a plain string -- mirrors realtime_session._stringify_tool_result
    (duplicated locally rather than imported to avoid coupling to that module's
    private helper)."""
    if isinstance(result, list):
        texts = [block.get("text", "") for block in result if isinstance(block, dict)]
        return "\n".join(t for t in texts if t) or str(result)
    return str(result)


def _first_error_line(error_block: str) -> str:
    """Pull just the "Error: ..." line out of execute_revit_code's verbose
    "=== ERROR DETAILS ===" block -- the full traceback is noise for the LLM
    and risks the same output-length problems that broke earlier wall creation."""
    for line in error_block.splitlines():
        if line.startswith("Error:"):
            return line[len("Error:") :].strip()
    return error_block[:200]


def _parse_or_error(raw: str) -> str:
    if raw.startswith(_ERROR_PREFIX):
        return json.dumps({"success": False, "error": _first_error_line(raw)})
    try:
        json.loads(raw)
        return raw
    except json.JSONDecodeError:
        return json.dumps({"success": False, "error": "Unexpected output: {0}".format(raw[:200])})


def _hosted_family_snippet(
    category: str,
    wall_id: str,
    position_ratio: float,
    family_name: str,
    type_name: str,
    id_field: str,
    label: str,
) -> str:
    """Shared snippet for create_door/create_window -- both need a HOSTED
    placement (doc.Create.NewFamilyInstance(point, symbol, wall, level, ...)),
    NOT the free-standing overload RevitMCP's own place_family tool uses
    (confirmed by reading RevitMCP.extension/revit_mcp/placement.py --
    place_family always calls NewFamilyInstance(point, symbol, level, ...)
    with no host, which is the wrong overload for door/window families and
    would fail or place them unhosted)."""
    return (
        "import json\n"
        "t = DB.Transaction(doc, {label!r})\n"
        "t.Start()\n"
        "try:\n"
        "    walls = DB.FilteredElementCollector(doc).OfClass(DB.Wall).ToElements()\n"
        "    wall = next((w for w in walls if str(w.Id) == {wall_id!r}), None)\n"
        "    if not wall:\n"
        "        t.RollBack()\n"
        "        ids = [str(w.Id) for w in walls][:40]\n"
        "        print(json.dumps({{'success': False, 'error': 'wall not found', 'available_wall_ids': ids}}))\n"
        "    else:\n"
        "        symbols = DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.{category})"
        ".OfClass(DB.FamilySymbol).ToElements()\n"
        "        symbol = next((s for s in symbols if {fam_expr} == {family_name!r} and {type_expr} == {type_name!r}), None)\n"
        "        if not symbol:\n"
        "            t.RollBack()\n"
        "            available = [{{'family': {fam_expr}, 'type': {type_expr}}} for s in symbols][:40]\n"
        "            print(json.dumps({{'success': False, 'error': 'type not found', 'available_types': available}}))\n"
        "        else:\n"
        "            if not symbol.IsActive:\n"
        "                symbol.Activate()\n"
        "                doc.Regenerate()\n"
        "            curve = wall.Location.Curve\n"
        "            point = curve.Evaluate({position_ratio!r}, True)\n"
        "            level = doc.GetElement(wall.LevelId)\n"
        "            instance = doc.Create.NewFamilyInstance(point, symbol, wall, level,"
        " DB.Structure.StructuralType.NonStructural)\n"
        "            t.Commit()\n"
        "            print(json.dumps({{'success': True, '{id_field}': str(instance.Id)}}))\n"
        "except Exception as ex:\n"
        "    t.RollBack()\n"
        "    print(json.dumps({{'success': False, 'error': str(ex)}}))\n"
    ).format(
        label=label,
        category=category,
        wall_id=wall_id,
        fam_expr=_NAME_EXPR.format("s.Family"),
        type_expr=_NAME_EXPR.format("s"),
        family_name=family_name,
        type_name=type_name,
        position_ratio=position_ratio,
        id_field=id_field,
    )


def build_revit_tools(execute_code: BaseTool) -> list[BaseTool]:
    """Returns the structured tool set, each closing over the already-open
    execute_revit_code MCP tool so they reuse its persistent RevitMCP
    session rather than opening a new one."""

    async def _run(code: str, description: str) -> str:
        raw = _extract_text(await execute_code.ainvoke({"code": code, "description": description}))
        return _parse_or_error(raw)

    @tool
    async def get_levels() -> str:
        """List every level in the current Revit model, with id, name, and elevation (feet)."""
        code = (
            "import json\n"
            "levels = DB.FilteredElementCollector(doc).OfClass(DB.Level).ToElements()\n"
            "out = [{{'id': str(l.Id), 'name': {name}, 'elevation': l.Elevation}} for l in levels]\n"
            "print(json.dumps(out))\n"
        ).format(name=_NAME_EXPR.format("l"))
        return await _run(code, "get_levels")

    @tool
    async def get_wall_types() -> str:
        """List every wall type available in the current Revit model, with id, name, and width (feet)."""
        code = (
            "import json\n"
            "types = DB.FilteredElementCollector(doc).OfClass(DB.WallType).ToElements()\n"
            "out = [{{'id': str(w.Id), 'name': {name}, 'width_ft': w.Width}} for w in types]\n"
            "print(json.dumps(out))\n"
        ).format(name=_NAME_EXPR.format("w"))
        return await _run(code, "get_wall_types")

    @tool
    async def get_walls() -> str:
        """List every wall currently placed in the model, with id, wall type, level, length (feet), and endpoints."""
        code = (
            "import json\n"
            "walls = DB.FilteredElementCollector(doc).OfClass(DB.Wall).ToElements()\n"
            "out = []\n"
            "for w in walls:\n"
            "    try:\n"
            "        curve = w.Location.Curve\n"
            "        p0 = curve.GetEndPoint(0)\n"
            "        p1 = curve.GetEndPoint(1)\n"
            "        level = doc.GetElement(w.LevelId)\n"
            "        out.append({{\n"
            "            'id': str(w.Id),\n"
            "            'type_name': {wall_type_name},\n"
            "            'level_name': {level_name},\n"
            "            'length_ft': curve.Length,\n"
            "            'start': [p0.X, p0.Y],\n"
            "            'end': [p1.X, p1.Y],\n"
            "        }})\n"
            "    except Exception:\n"
            "        out.append({{'id': str(w.Id), 'error': 'could not read geometry'}})\n"
            "print(json.dumps(out))\n"
        ).format(
            wall_type_name=_NAME_EXPR.format("w.WallType"),
            level_name=_NAME_EXPR.format("level") + " if level else 'N/A'",
        )
        return await _run(code, "get_walls")

    @tool
    async def get_rooms() -> str:
        """List every room in the model, with id, name, number, area (square feet), and level."""
        code = (
            "import json\n"
            "rooms = DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_Rooms)"
            ".WhereElementIsNotElementType().ToElements()\n"
            "out = []\n"
            "for r in rooms:\n"
            "    try:\n"
            "        level = doc.GetElement(r.LevelId)\n"
            "        out.append({{\n"
            "            'id': str(r.Id),\n"
            "            'name': {name},\n"
            "            'number': r.Number,\n"
            "            'area_sqft': r.Area,\n"
            "            'level_name': {level_name},\n"
            "        }})\n"
            "    except Exception:\n"
            "        out.append({{'id': str(r.Id), 'error': 'could not read room data'}})\n"
            "print(json.dumps(out))\n"
        ).format(
            name=_NAME_EXPR.format("r"),
            level_name=_NAME_EXPR.format("level") + " if level else 'N/A'",
        )
        return await _run(code, "get_rooms")

    @tool
    async def create_wall(
        start_x: float,
        start_y: float,
        end_x: float,
        end_y: float,
        level_name: str,
        wall_type_name: str,
        height_ft: float,
    ) -> str:
        """Create a straight wall between two points on a named level, using a named wall type.

        Coordinates and height are in feet (Revit's internal unit), in the
        project's shared coordinate system. level_name and wall_type_name
        must match an existing level/wall type exactly (case-sensitive) --
        call get_levels/get_wall_types first if unsure. If either name
        doesn't match, this returns the actual available names instead of
        creating anything, rather than guessing.
        """
        code = (
            "import json\n"
            "t = DB.Transaction(doc, 'REVVY create_wall')\n"
            "t.Start()\n"
            "try:\n"
            "    levels = DB.FilteredElementCollector(doc).OfClass(DB.Level).ToElements()\n"
            "    level = next((l for l in levels if {level_name_expr} == {level_name!r}), None)\n"
            "    if not level:\n"
            "        t.RollBack()\n"
            "        print(json.dumps({{'success': False, 'error': 'level not found',"
            " 'available_levels': [{level_name_expr} for l in levels]}}))\n"
            "    else:\n"
            "        wtypes = DB.FilteredElementCollector(doc).OfClass(DB.WallType).ToElements()\n"
            "        wtype = next((w for w in wtypes if {wall_type_name_expr} == {wall_type_name!r}), None)\n"
            "        if not wtype:\n"
            "            t.RollBack()\n"
            "            print(json.dumps({{'success': False, 'error': 'wall_type not found',"
            " 'available_wall_types': [{wall_type_name_expr} for w in wtypes]}}))\n"
            "        else:\n"
            "            p1 = DB.XYZ({start_x!r}, {start_y!r}, 0)\n"
            "            p2 = DB.XYZ({end_x!r}, {end_y!r}, 0)\n"
            "            curve = DB.Line.CreateBound(p1, p2)\n"
            "            wall = DB.Wall.Create(doc, curve, wtype.Id, level.Id, {height_ft!r}, 0.0, False, False)\n"
            "            t.Commit()\n"
            "            print(json.dumps({{'success': True, 'wall_id': str(wall.Id)}}))\n"
            "except Exception as ex:\n"
            "    t.RollBack()\n"
            "    print(json.dumps({{'success': False, 'error': str(ex)}}))\n"
        ).format(
            level_name_expr=_NAME_EXPR.format("l"),
            wall_type_name_expr=_NAME_EXPR.format("w"),
            level_name=level_name,
            wall_type_name=wall_type_name,
            start_x=start_x,
            start_y=start_y,
            end_x=end_x,
            end_y=end_y,
            height_ft=height_ft,
        )
        return await _run(code, "create_wall")

    @tool
    async def create_door(wall_id: str, position_ratio: float, family_name: str, type_name: str) -> str:
        """Place a door hosted in an existing wall.

        wall_id must match an existing wall's id (see get_walls). position_ratio
        is 0.0-1.0 for where along the wall's length to place the door (0 =
        start, 0.5 = middle, 1 = end). family_name/type_name must match an
        existing door family+type exactly (case-sensitive) -- call
        list_families(contains="door") first if unsure. If wall_id or the
        family/type doesn't match, this returns the actual available options
        instead of creating anything.
        """
        code = _hosted_family_snippet(
            "OST_Doors", wall_id, position_ratio, family_name, type_name, "door_id", "REVVY create_door"
        )
        return await _run(code, "create_door")

    @tool
    async def create_window(wall_id: str, position_ratio: float, family_name: str, type_name: str) -> str:
        """Place a window hosted in an existing wall.

        Same parameters as create_door: wall_id from get_walls, position_ratio
        0.0-1.0 along the wall's length, family_name/type_name matching an
        existing window family+type exactly (call list_families(contains="window")
        first if unsure).
        """
        code = _hosted_family_snippet(
            "OST_Windows", wall_id, position_ratio, family_name, type_name, "window_id", "REVVY create_window"
        )
        return await _run(code, "create_window")

    @tool
    async def create_room(x: float, y: float, level_name: str, name: str | None = None, number: str | None = None) -> str:
        """Place a room at a point on a named level, optionally naming/numbering it.

        A room only gets a real area once it's enclosed by a closed loop of
        walls at that point on that level -- create the surrounding walls
        with create_wall first if you want a real room, not just a marker.
        The result always includes area_sqft; if it comes back 0, the room
        was placed but isn't enclosed by walls, and you should say so rather
        than claiming it worked as a normal room.
        """
        # NewRoom at a point with no enclosing walls doesn't raise a catchable
        # exception -- confirmed live 2026-08-18: it instead pops a Revit
        # warning dialog that blocks the WHOLE document (not just this call)
        # until a human dismisses it in Revit's own UI, hanging RevitMCP's
        # request past its 60s timeout with no way for this process to
        # recover. IFailuresPreprocessor.DeleteWarning silently dismisses
        # every warning instead of showing it, so an unenclosed room just
        # comes back as a normal (if 0-area) success, matching what the
        # docstring above already promises.
        code = (
            "import json\n"
            "class _RevvySilentFailures(DB.IFailuresPreprocessor):\n"
            "    def PreprocessFailures(self, failuresAccessor):\n"
            "        for f in list(failuresAccessor.GetFailureMessages()):\n"
            "            failuresAccessor.DeleteWarning(f)\n"
            "        return DB.FailureProcessingResult.Continue\n"
            "t = DB.Transaction(doc, 'REVVY create_room')\n"
            "t.Start()\n"
            "opts = t.GetFailureHandlingOptions()\n"
            "opts.SetFailuresPreprocessor(_RevvySilentFailures())\n"
            "t.SetFailureHandlingOptions(opts)\n"
            "try:\n"
            "    levels = DB.FilteredElementCollector(doc).OfClass(DB.Level).ToElements()\n"
            "    level = next((l for l in levels if {level_name_expr} == {level_name!r}), None)\n"
            "    if not level:\n"
            "        t.RollBack()\n"
            "        print(json.dumps({{'success': False, 'error': 'level not found',"
            " 'available_levels': [{level_name_expr} for l in levels]}}))\n"
            "    else:\n"
            "        room = doc.Create.NewRoom(level, DB.UV({x!r}, {y!r}))\n"
            "        if {name!r}:\n"
            "            DB.Element.Name.__set__(room, {name!r})\n"
            "        if {number!r}:\n"
            "            room.Number = {number!r}\n"
            "        t.Commit()\n"
            "        print(json.dumps({{'success': True, 'room_id': str(room.Id), 'area_sqft': room.Area}}))\n"
            "except Exception as ex:\n"
            "    t.RollBack()\n"
            "    print(json.dumps({{'success': False, 'error': str(ex)}}))\n"
        ).format(
            level_name_expr=_NAME_EXPR.format("l"),
            level_name=level_name,
            x=x,
            y=y,
            name=name,
            number=number,
        )
        return await _run(code, "create_room")

    @tool
    async def create_property_line(width_ft: float, depth_ft: float, origin_x: float = 0.0, origin_y: float = 0.0) -> str:
        """Set the plot/property boundary as an axis-aligned rectangle, replacing any existing one.

        width_ft/depth_ft are the plot's size in feet; origin_x/origin_y (default
        0,0) is its corner. Replaces whatever property line already exists rather
        than adding another -- there's only ever one plot boundary. Needed before
        check_setbacks can measure anything (it has nothing to compare the
        building against otherwise).
        """
        # Live-checked 2026-08-18: property line elements are DB.PropertyLine
        # (category "Property Lines", NOT "Site" -- that guess found zero
        # elements even after a successful create), found via
        # OfClass(DB.PropertyLine) directly. PropertyLine.Create needs an IList[CurveLoop] -- a bare CurveLoop
        # (attempt 1) threw "expected IList[PropertyTableEntry], got
        # CurveLoop", and a plain Python list (attempt 2) threw "Multiple
        # targets could match" (ambiguous against the other Create
        # overload, IList[PropertyTableEntry] -- same class of ambiguity as
        # the ElementId(int) issue found earlier this session). A strongly
        # typed System.Collections.Generic.List[DB.CurveLoop] resolves it
        # unambiguously -- confirmed live 2026-08-18.
        code = (
            "import json\n"
            "import System\n"
            "class _RevvySilentFailures(DB.IFailuresPreprocessor):\n"
            "    def PreprocessFailures(self, failuresAccessor):\n"
            "        for f in list(failuresAccessor.GetFailureMessages()):\n"
            "            failuresAccessor.DeleteWarning(f)\n"
            "        return DB.FailureProcessingResult.Continue\n"
            "t = DB.Transaction(doc, 'REVVY create_property_line')\n"
            "t.Start()\n"
            "opts = t.GetFailureHandlingOptions()\n"
            "opts.SetFailuresPreprocessor(_RevvySilentFailures())\n"
            "t.SetFailureHandlingOptions(opts)\n"
            "try:\n"
            "    existing = DB.FilteredElementCollector(doc).OfClass(DB.PropertyLine).ToElements()\n"
            "    for e in list(existing):\n"
            "        doc.Delete(e.Id)\n"
            "    x0, y0 = {origin_x!r}, {origin_y!r}\n"
            "    x1, y1 = x0 + {width_ft!r}, y0 + {depth_ft!r}\n"
            "    corners = [DB.XYZ(x0, y0, 0), DB.XYZ(x1, y0, 0), DB.XYZ(x1, y1, 0), DB.XYZ(x0, y1, 0)]\n"
            "    loop = DB.CurveLoop()\n"
            "    for i in range(4):\n"
            "        loop.Append(DB.Line.CreateBound(corners[i], corners[(i + 1) % 4]))\n"
            "    loop_list = System.Collections.Generic.List[DB.CurveLoop]()\n"
            "    loop_list.Add(loop)\n"
            "    DB.PropertyLine.Create(doc, loop_list)\n"
            "    t.Commit()\n"
            "    print(json.dumps({{'success': True, 'corners': [[c.X, c.Y] for c in corners]}}))\n"
            "except Exception as ex:\n"
            "    t.RollBack()\n"
            "    print(json.dumps({{'success': False, 'error': str(ex)}}))\n"
        ).format(origin_x=origin_x, origin_y=origin_y, width_ft=width_ft, depth_ft=depth_ft)
        return await _run(code, "create_property_line")

    @tool
    async def get_plot_boundary() -> str:
        """Return the plot/property boundary's corner points, or boundary: null if none has been set (call create_property_line first)."""
        code = (
            "import json\n"
            "lines = []\n"
            "elems = DB.FilteredElementCollector(doc).OfClass(DB.PropertyLine).ToElements()\n"
            "for e in elems:\n"
            "    for loop in e.GetBoundary():\n"
            "        for curve in loop:\n"
            "            p0, p1 = curve.GetEndPoint(0), curve.GetEndPoint(1)\n"
            "            lines.append([[p0.X, p0.Y], [p1.X, p1.Y]])\n"
            "print(json.dumps({'boundary': lines if lines else None}))\n"
        )
        return await _run(code, "get_plot_boundary")

    @tool
    async def check_setbacks() -> str:
        """Return the actual distances (feet) from the building's wall envelope to each side of the plot boundary.

        Facts only -- this does NOT say whether the setbacks comply with
        TNCDBR. Always pair this with ask_building_code (for the actual
        required setback in this case) and compare them yourself; never
        assert compliance from this tool alone. Handles axis-aligned plots
        and buildings only. Returns an error if no plot boundary has been
        set yet (call create_property_line first) or if there are no walls.
        """
        code = (
            "import json\n"
            "boundary_pts = []\n"
            "elems = DB.FilteredElementCollector(doc).OfClass(DB.PropertyLine).ToElements()\n"
            "for e in elems:\n"
            "    for loop in e.GetBoundary():\n"
            "        for curve in loop:\n"
            "            boundary_pts.append(curve.GetEndPoint(0))\n"
            "            boundary_pts.append(curve.GetEndPoint(1))\n"
            "if not boundary_pts:\n"
            "    print(json.dumps({'error': 'no plot boundary set -- call create_property_line first'}))\n"
            "else:\n"
            "    walls = DB.FilteredElementCollector(doc).OfClass(DB.Wall).ToElements()\n"
            "    wall_pts = []\n"
            "    for w in walls:\n"
            "        try:\n"
            "            c = w.Location.Curve\n"
            "            wall_pts.append(c.GetEndPoint(0))\n"
            "            wall_pts.append(c.GetEndPoint(1))\n"
            "        except Exception:\n"
            "            pass\n"
            "    if not wall_pts:\n"
            "        print(json.dumps({'error': 'no walls in the model to measure setbacks from'}))\n"
            "    else:\n"
            "        plot_min_x = min(p.X for p in boundary_pts)\n"
            "        plot_max_x = max(p.X for p in boundary_pts)\n"
            "        plot_min_y = min(p.Y for p in boundary_pts)\n"
            "        plot_max_y = max(p.Y for p in boundary_pts)\n"
            "        bldg_min_x = min(p.X for p in wall_pts)\n"
            "        bldg_max_x = max(p.X for p in wall_pts)\n"
            "        bldg_min_y = min(p.Y for p in wall_pts)\n"
            "        bldg_max_y = max(p.Y for p in wall_pts)\n"
            "        print(json.dumps({\n"
            "            'left_ft': bldg_min_x - plot_min_x,\n"
            "            'right_ft': plot_max_x - bldg_max_x,\n"
            "            'front_ft': bldg_min_y - plot_min_y,\n"
            "            'rear_ft': plot_max_y - bldg_max_y,\n"
            "        }))\n"
        )
        return await _run(code, "check_setbacks")

    @tool
    async def get_element_location(element_id: str) -> str:
        """Return where any element is (start/end for a line-based element like a wall, or a point for a point-based one like a room/door/window), plus its category.

        element_id must match an existing element's id -- use get_walls/
        get_rooms/etc. to find valid ids, or an id returned by a create_*/
        move_element call.
        """
        code = (
            "import json\n"
            + _FIND_ELEMENT
            + "if not el:\n"
            "    print(json.dumps({{'error': 'element not found', 'id': {element_id!r}}}))\n"
            "else:\n"
            "    cat = el.Category.Name if el.Category else None\n"
            "    loc = el.Location\n"
            "    curve = getattr(loc, 'Curve', None)\n"
            "    point = getattr(loc, 'Point', None)\n"
            "    if curve:\n"
            "        p0, p1 = curve.GetEndPoint(0), curve.GetEndPoint(1)\n"
            "        print(json.dumps({{'category': cat, 'start': [p0.X, p0.Y], 'end': [p1.X, p1.Y]}}))\n"
            "    elif point:\n"
            "        print(json.dumps({{'category': cat, 'point': [point.X, point.Y]}}))\n"
            "    else:\n"
            "        print(json.dumps({{'category': cat, 'location': None}}))\n"
        ).format(element_id=element_id)
        return await _run(code, "get_element_location")

    @tool
    async def get_element_geometry(element_id: str) -> str:
        """Return an element's 3D bounding box (min/max corner in feet) and category -- its actual extent, not just a location point."""
        code = (
            "import json\n"
            + _FIND_ELEMENT
            + "if not el:\n"
            "    print(json.dumps({{'error': 'element not found', 'id': {element_id!r}}}))\n"
            "else:\n"
            "    cat = el.Category.Name if el.Category else None\n"
            "    bbox = el.get_BoundingBox(None)\n"
            "    if bbox:\n"
            "        print(json.dumps({{'category': cat, 'min': [bbox.Min.X, bbox.Min.Y, bbox.Min.Z],"
            " 'max': [bbox.Max.X, bbox.Max.Y, bbox.Max.Z]}}))\n"
            "    else:\n"
            "        print(json.dumps({{'category': cat, 'error': 'no bounding box available for this element'}}))\n"
        ).format(element_id=element_id)
        return await _run(code, "get_element_geometry")

    @tool
    async def move_element(element_id: str, dx: float, dy: float, dz: float = 0.0) -> str:
        """Move any element by a relative offset in feet (dx, dy, dz). Returns its new location so you can confirm where it ended up.

        Use this for corrections ("move that wall 2 feet east") instead of
        deleting and recreating the element.
        """
        code = (
            "import json\n"
            "class _RevvySilentFailures(DB.IFailuresPreprocessor):\n"
            "    def PreprocessFailures(self, failuresAccessor):\n"
            "        for f in list(failuresAccessor.GetFailureMessages()):\n"
            "            failuresAccessor.DeleteWarning(f)\n"
            "        return DB.FailureProcessingResult.Continue\n"
            + _FIND_ELEMENT
            + "if not el:\n"
            "    print(json.dumps({{'success': False, 'error': 'element not found', 'id': {element_id!r}}}))\n"
            "else:\n"
            "    t = DB.Transaction(doc, 'REVVY move_element')\n"
            "    t.Start()\n"
            "    opts = t.GetFailureHandlingOptions()\n"
            "    opts.SetFailuresPreprocessor(_RevvySilentFailures())\n"
            "    t.SetFailureHandlingOptions(opts)\n"
            "    try:\n"
            "        DB.ElementTransformUtils.MoveElement(doc, el.Id, DB.XYZ({dx!r}, {dy!r}, {dz!r}))\n"
            "        t.Commit()\n"
            "        loc = el.Location\n"
            "        curve = getattr(loc, 'Curve', None)\n"
            "        point = getattr(loc, 'Point', None)\n"
            "        if curve:\n"
            "            p0, p1 = curve.GetEndPoint(0), curve.GetEndPoint(1)\n"
            "            print(json.dumps({{'success': True, 'start': [p0.X, p0.Y], 'end': [p1.X, p1.Y]}}))\n"
            "        elif point:\n"
            "            print(json.dumps({{'success': True, 'point': [point.X, point.Y]}}))\n"
            "        else:\n"
            "            print(json.dumps({{'success': True}}))\n"
            "    except Exception as ex:\n"
            "        t.RollBack()\n"
            "        print(json.dumps({{'success': False, 'error': str(ex)}}))\n"
        ).format(element_id=element_id, dx=dx, dy=dy, dz=dz)
        return await _run(code, "move_element")

    @tool
    async def delete_element(element_id: str) -> str:
        """Delete any element by id. Deleting a wall also deletes any door/window hosted on it (Revit's own behavior)."""
        code = (
            "import json\n"
            + _FIND_ELEMENT
            + "if not el:\n"
            "    print(json.dumps({{'success': False, 'error': 'element not found', 'id': {element_id!r}}}))\n"
            "else:\n"
            "    t = DB.Transaction(doc, 'REVVY delete_element')\n"
            "    t.Start()\n"
            "    try:\n"
            "        doc.Delete(el.Id)\n"
            "        t.Commit()\n"
            "        print(json.dumps({{'success': True, 'deleted_id': {element_id!r}}}))\n"
            "    except Exception as ex:\n"
            "        t.RollBack()\n"
            "        print(json.dumps({{'success': False, 'error': str(ex)}}))\n"
        ).format(element_id=element_id)
        return await _run(code, "delete_element")

    @tool
    async def modify_wall(
        wall_id: str,
        wall_type_name: str | None = None,
        height_ft: float | None = None,
        start_x: float | None = None,
        start_y: float | None = None,
        end_x: float | None = None,
        end_y: float | None = None,
    ) -> str:
        """Change an existing wall's type, height, and/or endpoints -- only the fields you provide are changed.

        To move an endpoint, provide all four of start_x/start_y/end_x/end_y
        together (a full new line), not just one coordinate. wall_type_name
        must match an existing wall type exactly -- call get_wall_types first
        if unsure; if it doesn't match, this returns the actual available
        types instead of guessing, same as create_wall.
        """
        code = (
            "import json\n"
            "class _RevvySilentFailures(DB.IFailuresPreprocessor):\n"
            "    def PreprocessFailures(self, failuresAccessor):\n"
            "        for f in list(failuresAccessor.GetFailureMessages()):\n"
            "            failuresAccessor.DeleteWarning(f)\n"
            "        return DB.FailureProcessingResult.Continue\n"
            "walls = DB.FilteredElementCollector(doc).OfClass(DB.Wall).ToElements()\n"
            "wall = next((w for w in walls if str(w.Id) == {wall_id!r}), None)\n"
            "if not wall:\n"
            "    print(json.dumps({{'success': False, 'error': 'wall not found',"
            " 'available_wall_ids': [str(w.Id) for w in walls][:40]}}))\n"
            "else:\n"
            "    t = DB.Transaction(doc, 'REVVY modify_wall')\n"
            "    t.Start()\n"
            "    opts = t.GetFailureHandlingOptions()\n"
            "    opts.SetFailuresPreprocessor(_RevvySilentFailures())\n"
            "    t.SetFailureHandlingOptions(opts)\n"
            "    try:\n"
            "        ok, err, available = True, None, None\n"
            "        if {wall_type_name!r}:\n"
            "            wtypes = DB.FilteredElementCollector(doc).OfClass(DB.WallType).ToElements()\n"
            "            wtype = next((w for w in wtypes if {wall_type_name_expr} == {wall_type_name!r}), None)\n"
            "            if not wtype:\n"
            "                ok, err = False, 'wall_type not found'\n"
            "                available = [{wall_type_name_expr} for w in wtypes]\n"
            "            else:\n"
            "                wall.ChangeTypeId(wtype.Id)\n"
            "        if ok and {height_ft!r} is not None:\n"
            "            wall.get_Parameter(DB.BuiltInParameter.WALL_USER_HEIGHT_PARAM).Set({height_ft!r})\n"
            "        if ok and {start_x!r} is not None and {start_y!r} is not None"
            " and {end_x!r} is not None and {end_y!r} is not None:\n"
            "            p1 = DB.XYZ({start_x!r}, {start_y!r}, 0)\n"
            "            p2 = DB.XYZ({end_x!r}, {end_y!r}, 0)\n"
            "            wall.Location.Curve = DB.Line.CreateBound(p1, p2)\n"
            "        if not ok:\n"
            "            t.RollBack()\n"
            "            print(json.dumps({{'success': False, 'error': err, 'available_wall_types': available}}))\n"
            "        else:\n"
            "            t.Commit()\n"
            "            curve = wall.Location.Curve\n"
            "            p0, p1e = curve.GetEndPoint(0), curve.GetEndPoint(1)\n"
            "            print(json.dumps({{'success': True, 'wall_id': str(wall.Id),"
            " 'type_name': {wall_type_name_expr2}, 'start': [p0.X, p0.Y], 'end': [p1e.X, p1e.Y]}}))\n"
            "    except Exception as ex:\n"
            "        t.RollBack()\n"
            "        print(json.dumps({{'success': False, 'error': str(ex)}}))\n"
        ).format(
            wall_id=wall_id,
            wall_type_name_expr=_NAME_EXPR.format("w"),
            wall_type_name_expr2=_NAME_EXPR.format("wall.WallType"),
            wall_type_name=wall_type_name,
            height_ft=height_ft,
            start_x=start_x,
            start_y=start_y,
            end_x=end_x,
            end_y=end_y,
        )
        return await _run(code, "modify_wall")

    @tool
    async def modify_room(room_id: str, name: str | None = None, number: str | None = None) -> str:
        """Rename and/or renumber an existing room -- only the fields you provide are changed."""
        code = (
            "import json\n"
            "rooms = DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_Rooms)"
            ".WhereElementIsNotElementType().ToElements()\n"
            "room = next((r for r in rooms if str(r.Id) == {room_id!r}), None)\n"
            "if not room:\n"
            "    print(json.dumps({{'success': False, 'error': 'room not found',"
            " 'available_room_ids': [str(r.Id) for r in rooms][:40]}}))\n"
            "else:\n"
            "    t = DB.Transaction(doc, 'REVVY modify_room')\n"
            "    t.Start()\n"
            "    try:\n"
            "        if {name!r}:\n"
            "            DB.Element.Name.__set__(room, {name!r})\n"
            "        if {number!r}:\n"
            "            room.Number = {number!r}\n"
            "        t.Commit()\n"
            "        print(json.dumps({{'success': True, 'room_id': str(room.Id),"
            " 'name': {name_expr}, 'number': room.Number, 'area_sqft': room.Area}}))\n"
            "    except Exception as ex:\n"
            "        t.RollBack()\n"
            "        print(json.dumps({{'success': False, 'error': str(ex)}}))\n"
        ).format(room_id=room_id, name=name, number=number, name_expr=_NAME_EXPR.format("room"))
        return await _run(code, "modify_room")

    @tool
    async def create_floor_plan(
        rooms: list[RoomSpec], level_name: str, wall_type_name: str, height_ft: float
    ) -> str:
        """Create multiple rooms (walls + room elements) in one batch, instead of calling create_wall/create_room repeatedly.

        You decide the layout yourself (each room's x/y corner and width_ft/
        depth_ft) -- this tool just builds it, atomically: either the whole
        floor plan is created or none of it is (any error rolls back
        everything). All rooms use the same level_name and wall_type_name and
        height_ft; use modify_wall afterward if specific walls need a
        different type. Rooms are NOT wall-deduplicated -- two adjacent rooms
        sharing an edge each get their own walls there (doubled, not shared).
        Doors/windows are not included -- add them afterward with
        create_door/create_window using the wall_ids this returns.
        """
        code = (
            "import json\n"
            "class _RevvySilentFailures(DB.IFailuresPreprocessor):\n"
            "    def PreprocessFailures(self, failuresAccessor):\n"
            "        for f in list(failuresAccessor.GetFailureMessages()):\n"
            "            failuresAccessor.DeleteWarning(f)\n"
            "        return DB.FailureProcessingResult.Continue\n"
            "levels = DB.FilteredElementCollector(doc).OfClass(DB.Level).ToElements()\n"
            "level = next((l for l in levels if {level_name_expr} == {level_name!r}), None)\n"
            "if not level:\n"
            "    print(json.dumps({{'success': False, 'error': 'level not found',"
            " 'available_levels': [{level_name_expr} for l in levels]}}))\n"
            "else:\n"
            "    wtypes = DB.FilteredElementCollector(doc).OfClass(DB.WallType).ToElements()\n"
            "    wtype = next((w for w in wtypes if {wall_type_name_expr} == {wall_type_name!r}), None)\n"
            "    if not wtype:\n"
            "        print(json.dumps({{'success': False, 'error': 'wall_type not found',"
            " 'available_wall_types': [{wall_type_name_expr} for w in wtypes]}}))\n"
            "    else:\n"
            "        rooms_spec = json.loads({rooms_json!r})\n"
            "        t = DB.Transaction(doc, 'REVVY create_floor_plan')\n"
            "        t.Start()\n"
            "        opts = t.GetFailureHandlingOptions()\n"
            "        opts.SetFailuresPreprocessor(_RevvySilentFailures())\n"
            "        t.SetFailureHandlingOptions(opts)\n"
            "        try:\n"
            "            results = []\n"
            "            for r in rooms_spec:\n"
            "                x, y, w, d = r['x'], r['y'], r['width_ft'], r['depth_ft']\n"
            "                corners = [DB.XYZ(x, y, 0), DB.XYZ(x + w, y, 0), DB.XYZ(x + w, y + d, 0), DB.XYZ(x, y + d, 0)]\n"
            "                wall_ids = []\n"
            "                for i in range(4):\n"
            "                    curve = DB.Line.CreateBound(corners[i], corners[(i + 1) % 4])\n"
            "                    wall = DB.Wall.Create(doc, curve, wtype.Id, level.Id, {height_ft!r}, 0.0, False, False)\n"
            "                    wall_ids.append(str(wall.Id))\n"
            "                room = doc.Create.NewRoom(level, DB.UV(x + w / 2.0, y + d / 2.0))\n"
            "                if r.get('name'):\n"
            "                    DB.Element.Name.__set__(room, r['name'])\n"
            "                if r.get('number'):\n"
            "                    room.Number = r['number']\n"
            "                results.append({{'name': r.get('name'), 'wall_ids': wall_ids,"
            " 'room_id': str(room.Id), 'area_sqft': room.Area}})\n"
            "            t.Commit()\n"
            "            print(json.dumps({{'success': True, 'rooms': results}}))\n"
            "        except Exception as ex:\n"
            "            t.RollBack()\n"
            "            print(json.dumps({{'success': False, 'error': str(ex)}}))\n"
        ).format(
            level_name_expr=_NAME_EXPR.format("l"),
            level_name=level_name,
            wall_type_name_expr=_NAME_EXPR.format("w"),
            wall_type_name=wall_type_name,
            rooms_json=json.dumps([r.model_dump() for r in rooms]),
            height_ft=height_ft,
        )
        return await _run(code, "create_floor_plan")

    return [
        get_levels,
        get_wall_types,
        get_walls,
        get_rooms,
        create_wall,
        create_door,
        create_window,
        create_room,
        create_property_line,
        get_plot_boundary,
        check_setbacks,
        get_element_location,
        get_element_geometry,
        move_element,
        delete_element,
        modify_wall,
        modify_room,
        create_floor_plan,
    ]
