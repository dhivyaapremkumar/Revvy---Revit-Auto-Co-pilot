# -*- coding: utf-8 -*-
"""REVVY Model Query -- read-only natural-language queries against the open model.

STRICTLY READ-ONLY. This script (and everything it calls in
revvy.revit_model) must never open a Revit Transaction. Cheap local model
context (document title, active view, basic element counts via
FilteredElementCollector) is gathered and folded into the `query` text sent
to the backend, since the fixed `/model/query` request contract is exactly
`{"revit_project_name": str, "query": str}` with no separate context field.

Uses :mod:`revvy.ui` rather than ``pyrevit.forms``/``script.get_output()`` --
see the module docstring in ``revvy/ui.py`` for why.
"""
import json

from revvy import api_client, auth_ui, revit_model, ui
from revvy.api_client import AuthenticationError, RevvyApiError
from revvy.revit_model import RevitHostUnavailableError


def main():
    if not auth_ui.ensure_authenticated():
        return

    try:
        project_name = revit_model.get_project_name()
        context = revit_model.gather_model_context()
    except RevitHostUnavailableError as exc:
        ui.alert(str(exc), title="REVVY Model Query - Error")
        return

    query_text = ui.ask_string(
        prompt="Ask a question about the open model:",
        title="REVVY Model Query",
    )
    if not query_text:
        return

    context_note = "[Context: document='{0}', active_view='{1}', counts={2}]\n\n".format(
        context["document_title"], context["active_view"], json.dumps(context["element_counts"])
    )
    full_query = context_note + query_text

    try:
        result = api_client.query_model(project_name, full_query)
    except AuthenticationError:
        ui.alert(
            "Your REVVY session expired. Run REVVY Model Query again to log back in.",
            title="REVVY Model Query - Error",
        )
        return
    except RevvyApiError as exc:
        ui.alert(str(exc), title="REVVY Model Query - Error")
        return

    answer = result.get("answer") or result.get("result") or result
    ui.show_report(
        main_instruction="REVVY Model Query",
        content="Query: {0}\n\nAnswer:\n{1}".format(query_text, answer),
        title="REVVY Model Query",
    )


main()
