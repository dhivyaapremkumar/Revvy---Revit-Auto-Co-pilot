# -*- coding: utf-8 -*-
"""Backend URL + per-user auth token storage for the REVVY pyRevit add-in.

Storage strategy (in priority order):

1. **pyRevit script config** (`pyrevit.script.get_config`) — the idiomatic
   pyRevit way to persist small bits of state. It writes into pyRevit's own
   config file under the current Windows user's ``%APPDATA%\\pyRevit``
   profile, so it is *inherently* per-user: two different Windows logins on
   the same machine never see each other's token, and nothing is ever
   embedded in the extension source or shared between installs.
2. **JSON file fallback** — used when running outside a live pyRevit/Revit
   host (e.g. this sandbox has no Revit install), or if the pyRevit config
   API is unavailable/changes shape across versions. The fallback file lives
   at ``%APPDATA%\\REVVY\\addin_config.json`` (or ``$HOME/.revvy`` on
   non-Windows), which is likewise scoped to the OS user account.

The backend base URL can also be overridden with the ``REVVY_BACKEND_URL``
environment variable (matches the variable name used by the FastAPI backend
docs / .env.example), so the same extension works against a local dev
server or a deployed backend without editing code.

CRITICAL: the token stored here is a *per-user* JWT access token obtained by
the user logging in (web dashboard or the in-Revit login form). It must
never be hardcoded, checked into source control, or copied between users.
"""
import io
import json
import os

DEFAULT_BACKEND_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"
ENV_BACKEND_URL = "REVVY_BACKEND_URL"

_CONFIG_SECTION = "revvy"
_TOKEN_KEY = "auth_token"
_URL_KEY = "backend_url"


def _fallback_config_path():
    """Return the per-OS-user path used when pyRevit's config API is unavailable."""
    root = os.environ.get("APPDATA") or os.path.expanduser("~")
    folder = os.path.join(root, "REVVY")
    try:
        os.makedirs(folder)
    except OSError:
        pass
    return os.path.join(folder, "addin_config.json")


def _read_fallback():
    path = _fallback_config_path()
    if not os.path.isfile(path):
        return {}
    try:
        with io.open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return {}


def _write_fallback(data):
    path = _fallback_config_path()
    try:
        with io.open(path, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(data))
    except OSError:
        pass


def _pyrevit_config():
    """Return pyRevit's persistent config section for REVVY, or None if unavailable.

    Wrapped defensively: this module must still import and behave sanely
    when pyRevit is not on ``sys.path`` (e.g. static validation outside
    Revit), and the pyRevit config API has shifted shape across versions.
    """
    try:
        from pyrevit import script  # type: ignore

        cfg = script.get_config(_CONFIG_SECTION)
        return cfg
    except Exception:
        return None


def get_backend_url():
    """Return the configured backend base URL (no trailing slash)."""
    env_value = os.environ.get(ENV_BACKEND_URL)
    if env_value:
        return env_value.rstrip("/")

    cfg = _pyrevit_config()
    if cfg is not None:
        stored = getattr(cfg, _URL_KEY, None)
        if stored:
            return str(stored).rstrip("/")

    stored = _read_fallback().get(_URL_KEY)
    if stored:
        return str(stored).rstrip("/")

    return DEFAULT_BACKEND_URL


def set_backend_url(url):
    """Persist a custom backend base URL for this Windows user."""
    url = url.rstrip("/")
    cfg = _pyrevit_config()
    if cfg is not None:
        try:
            from pyrevit import script  # type: ignore

            setattr(cfg, _URL_KEY, url)
            script.save_config()
            return
        except Exception:
            pass

    data = _read_fallback()
    data[_URL_KEY] = url
    _write_fallback(data)


def get_token():
    """Return the stored per-user JWT access token, or None if not logged in."""
    cfg = _pyrevit_config()
    if cfg is not None:
        stored = getattr(cfg, _TOKEN_KEY, None)
        if stored:
            return str(stored)

    return _read_fallback().get(_TOKEN_KEY)


def set_token(token):
    """Persist a per-user JWT access token. Never call this with a shared/service token."""
    cfg = _pyrevit_config()
    if cfg is not None:
        try:
            from pyrevit import script  # type: ignore

            setattr(cfg, _TOKEN_KEY, token)
            script.save_config()
            return
        except Exception:
            pass

    data = _read_fallback()
    data[_TOKEN_KEY] = token
    _write_fallback(data)


def clear_token():
    """Log the current Windows user out of the add-in (does not affect other users)."""
    cfg = _pyrevit_config()
    if cfg is not None:
        try:
            from pyrevit import script  # type: ignore

            setattr(cfg, _TOKEN_KEY, None)
            script.save_config()
        except Exception:
            pass

    data = _read_fallback()
    data.pop(_TOKEN_KEY, None)
    _write_fallback(data)


def is_authenticated():
    """True if a token has been stored for the current Windows user."""
    return bool(get_token())


def api_url(path):
    """Join the backend base URL + API prefix + a path like '/chat/sessions'."""
    if not path.startswith("/"):
        path = "/" + path
    return "{0}{1}{2}".format(get_backend_url(), API_PREFIX, path)
