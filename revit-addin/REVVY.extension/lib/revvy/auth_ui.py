# -*- coding: utf-8 -*-
"""Shared login dialog used by every REVVY pushbutton before it calls the backend.

KNOWN LIMITATION (flag for real-Revit review): the hand-built WinForms
password textbox in :mod:`revvy.ui` masks input with ``UseSystemPasswordChar``,
so the password is never shown in plain text. Only the resulting JWT is
persisted (via ``revvy.config``) -- the password itself is never written to
disk.
"""
from revvy import api_client, config, ui
from revvy.api_client import RevvyApiError


def ensure_authenticated():
    """Return True once the current Windows user has a valid stored token.

    If no token is stored yet (first run, or after `revvy.config.clear_token`),
    prompts for email/password and logs in via `POST /api/v1/auth/login`,
    storing the returned per-user token. Never prompts again until the token
    is cleared or the backend rejects it (see AuthenticationError handling
    in each pushbutton's script.py).
    """
    if config.is_authenticated():
        return True

    email = ui.ask_string(prompt="REVVY email:", title="REVVY Login")
    if not email:
        return False
    password = ui.ask_string(prompt="REVVY password:", title="REVVY Login", is_password=True)
    if not password:
        return False

    try:
        api_client.login(email, password)
    except RevvyApiError as exc:
        ui.alert("Login failed: {0}".format(exc), title="REVVY Login - Error")
        return False

    return True
