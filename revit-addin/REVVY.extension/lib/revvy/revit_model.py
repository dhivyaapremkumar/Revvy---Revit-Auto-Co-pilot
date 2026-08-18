# -*- coding: utf-8 -*-
"""Revit-API helpers: read-only model context for Model Query.

============================================================================
Revit host availability
============================================================================
This module can only truly execute inside pyRevit running in Revit (it
needs ``Autodesk.Revit.DB`` and the active ``UIDocument``). Imports are
guarded so the file still *parses and imports* in this sandbox (no Revit
installed here); any function that touches the Revit API raises
``RevitHostUnavailableError`` if called outside a real host.
"""
try:  # pragma: no cover - only available inside pyRevit/Revit
    from pyrevit import revit, DB  # type: ignore

    _HAS_REVIT = True
except ImportError:  # pragma: no cover
    revit = None  # type: ignore
    DB = None  # type: ignore
    _HAS_REVIT = False


class RevitHostUnavailableError(RuntimeError):
    """Raised when Revit-API-dependent code runs outside a real Revit/pyRevit host."""


def _require_revit():
    if not _HAS_REVIT:
        raise RevitHostUnavailableError(
            "Autodesk.Revit.DB / pyrevit is not available. This function must "
            "run inside pyRevit hosted by Revit."
        )


# ---------------------------------------------------------------------------
# Read-only helpers (Model Query) — MUST NEVER open a Transaction
# ---------------------------------------------------------------------------


def get_active_document():
    """Return the active Revit Document, or raise if no host/document is available."""
    _require_revit()
    doc = revit.doc
    if doc is None:
        raise RevitHostUnavailableError("No active Revit document is open.")
    return doc


def get_project_name(doc=None):
    """Best-effort project/document name to send as `revit_project_name`."""
    _require_revit()
    doc = doc or get_active_document()
    title = getattr(doc, "Title", None)
    return title or "Untitled"


def get_active_view_name(doc=None):
    _require_revit()
    doc = doc or get_active_document()
    try:
        active_view = revit.active_view
    except Exception:
        active_view = doc.ActiveView
    try:
        return _element_name(active_view)
    except Exception:
        return "Unknown"


def get_basic_counts(doc=None):
    """Cheap element counts via FilteredElementCollector, for Model Query context.

    Strictly read-only: only ever calls FilteredElementCollector queries,
    never opens a Transaction.
    """
    _require_revit()
    doc = doc or get_active_document()

    def _count(category):
        return (
            DB.FilteredElementCollector(doc)
            .OfCategory(category)
            .WhereElementIsNotElementType()
            .GetElementCount()
        )

    return {
        "walls": _count(DB.BuiltInCategory.OST_Walls),
        "doors": _count(DB.BuiltInCategory.OST_Doors),
        "windows": _count(DB.BuiltInCategory.OST_Windows),
        "rooms": _count(DB.BuiltInCategory.OST_Rooms),
        "levels": _count(DB.BuiltInCategory.OST_Levels),
        "stairs": _count(DB.BuiltInCategory.OST_Stairs),
    }


def gather_model_context(doc=None):
    """Assemble the cheap local context sent alongside a `/model/query` request.

    Read-only. Safe to call from ModelQuery.pushbutton before every query.
    """
    _require_revit()
    doc = doc or get_active_document()
    return {
        "document_title": get_project_name(doc),
        "active_view": get_active_view_name(doc),
        "element_counts": get_basic_counts(doc),
    }


def _element_name(element):
    """Read an Element's ``.Name`` safely across engines.

    Under this IronPython engine, ``Element.Name`` is explicitly-implemented
    on some Revit API types (observed on ``FamilySymbol``, not on
    ``WallType``) in a way normal instance attribute access can't resolve --
    it raises ``AttributeError: Name`` instead of returning the string.
    ``DB.Element.Name.__get__(element)`` reads the property descriptor
    directly off the base ``Element`` class, bypassing whatever breaks the
    instance lookup.
    """
    try:
        return element.Name
    except AttributeError:
        return DB.Element.Name.__get__(element)
