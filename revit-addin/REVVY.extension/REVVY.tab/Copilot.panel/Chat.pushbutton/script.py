# -*- coding: utf-8 -*-
"""REVVY Chat -- chat copilot loop, calling the shared /chat endpoints.

Uses :mod:`revvy.ui` (native TaskDialog + a hand-built WinForms input box)
rather than ``pyrevit.forms``/``script.get_output()`` -- see the module
docstring in ``revvy/ui.py`` for why. Session picking is simplified to
"continue most recent" vs. "start new" (a TaskDialog can't show an
arbitrary-length list the way ``forms.SelectFromList`` could): pick or
start a session, then loop on ask_string -> send message -> show reply,
until the user cancels the input dialog.
"""
import datetime

from revvy import api_client, auth_ui, revit_model, ui
from revvy.api_client import AuthenticationError, RevvyApiError
from revvy.revit_model import RevitHostUnavailableError

try:
    _string_types = (str, unicode)  # noqa: F821 - unicode only exists on Python 2
except NameError:
    _string_types = (str,)


def _project_name():
    try:
        return revit_model.get_project_name()
    except RevitHostUnavailableError:
        return None


def _default_title(project_name):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    if project_name:
        return "{0} - {1}".format(project_name, timestamp)
    return "REVVY Chat - {0}".format(timestamp)


def _pick_or_create_session():
    try:
        sessions = api_client.list_chat_sessions() or []
    except RevvyApiError as exc:
        ui.alert(str(exc), title="REVVY Chat - Error")
        return None

    if sessions:
        most_recent = sessions[0]
        label = "#{0} - {1}".format(
            most_recent.get("id"), most_recent.get("title") or "Untitled"
        )
        if ui.confirm(
            "Continue most recent session ({0})?\n\nChoose No to start a new session.".format(
                label
            ),
            title="REVVY Chat",
        ):
            return most_recent

    project_name = _project_name()
    try:
        return api_client.create_chat_session(
            title=_default_title(project_name), revit_project_name=project_name
        )
    except RevvyApiError as exc:
        ui.alert(str(exc), title="REVVY Chat - Error")
        return None


def _extract_assistant_reply(result):
    """Defensive extraction: the exact response schema is still being
    finalized by BACKEND-AGENT, so this checks a few plausible shapes
    instead of hardcoding one."""
    if isinstance(result, dict):
        for key in ("assistant_message", "reply", "message"):
            value = result.get(key)
            if isinstance(value, dict) and "content" in value:
                return value["content"]
            if isinstance(value, _string_types):
                return value
        if "content" in result:
            return result["content"]
    return str(result)


def main():
    if not auth_ui.ensure_authenticated():
        return

    session = _pick_or_create_session()
    if not session:
        return

    session_id = session.get("id")

    while True:
        user_text = ui.ask_string(
            prompt="Message REVVY (Cancel to end chat):",
            title="REVVY Chat - Session #{0}".format(session_id),
        )
        if not user_text:
            break

        try:
            result = api_client.send_chat_message(session_id, user_text)
        except AuthenticationError:
            ui.alert(
                "Your REVVY session expired. Run REVVY Chat again to log back in.",
                title="REVVY Chat - Error",
            )
            break
        except RevvyApiError as exc:
            ui.alert(str(exc), title="REVVY Chat - Error")
            continue

        reply = _extract_assistant_reply(result)
        if not ui.confirm(
            "{0}\n\nContinue chatting?".format(reply),
            title="REVVY Chat - Session #{0}".format(session_id),
        ):
            break


main()
