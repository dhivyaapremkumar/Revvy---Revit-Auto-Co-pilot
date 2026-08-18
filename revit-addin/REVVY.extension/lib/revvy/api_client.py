# -*- coding: utf-8 -*-
"""Thin HTTP client for the REVVY FastAPI backend, used by all three pushbuttons.

Every call attaches ``Authorization: Bearer <token>`` using the per-user
token from :mod:`revvy.config`. Never call the backend with a hardcoded or
shared token — the caller is responsible for prompting the user to log in
(see :func:`login`) when :func:`revvy.config.is_authenticated` is False.

Transport: always uses the standard library (``urllib2``/``urllib.request``),
never the third-party ``requests`` library, even when it's importable.
pyRevit's bundled ``requests``+``chardet`` under IronPython has a known
incompatibility -- IronPython's response stream hands back a ``unicode``
string where ``chardet.detect()`` expects raw bytes, raising
``ValueError: Expected a bytes object, not a unicode object`` the moment
``response.text`` is touched. The stdlib fallback works identically under
IronPython 2/3, CPython, and outside Revit entirely (for the static
validation done in this sandbox).

Endpoint contract (fixed by BACKEND-AGENT, documented in PRPs/revvy-prp.md
Modules 1/2):

- ``POST /api/v1/auth/login``               {"email", "password"} -> {"access_token", "token_type", ...}
- ``GET  /api/v1/chat/sessions``             -> list[ChatSession]
- ``POST /api/v1/chat/sessions``             {"title"?, "revit_project_name"?} -> ChatSession
- ``POST /api/v1/chat/sessions/{id}/messages`` {"content"} -> {message, assistant reply}
- ``POST /api/v1/model/query``               {"revit_project_name", "query"} -> query result (read-only)

The exact response schemas are still being finalized by BACKEND-AGENT in
parallel; this client treats all JSON responses as loosely-typed dicts and
lets callers (the pushbutton scripts) pull out the fields they need
defensively, rather than hardcoding a strict schema that may drift.
"""
import json as _json
import socket as _socket

from revvy import config

try:  # Python 3 / IronPython 3
    import urllib.request as _urllib_request
    import urllib.error as _urllib_error
except ImportError:  # Python 2 / IronPython 2
    import urllib2 as _urllib_request  # type: ignore

    _urllib_error = _urllib_request


class _MethodRequest(_urllib_request.Request):
    """Request subclass that lets us force GET/POST explicitly.

    Needed because Python 2's ``urllib2.Request`` has no ``method=`` kwarg
    (added in Python 3.3+) -- it infers GET/POST solely from whether
    ``data`` is None, which happens to match every call this client makes,
    but being explicit avoids relying on that coincidence.
    """

    def __init__(self, method, *args, **kwargs):
        self._method = method
        _urllib_request.Request.__init__(self, *args, **kwargs)

    def get_method(self):
        return self._method


DEFAULT_TIMEOUT_SECONDS = 30


class RevvyApiError(Exception):
    """Raised for any non-2xx response or transport failure talking to the backend."""

    def __init__(self, message, status_code=None, payload=None):
        super(RevvyApiError, self).__init__(message)
        self.status_code = status_code
        self.payload = payload or {}


class AuthenticationError(RevvyApiError):
    """Raised on 401/403 -- the stored token is missing, expired, or invalid."""


def _headers(include_auth=True):
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if include_auth:
        token = config.get_token()
        if token:
            headers["Authorization"] = "Bearer {0}".format(token)
    return headers


def _request(method, path, json_body=None, include_auth=True, timeout=DEFAULT_TIMEOUT_SECONDS):
    """Perform one HTTP call against the backend and return the decoded JSON body.

    Raises AuthenticationError on 401/403, RevvyApiError on any other
    non-2xx response or network/transport failure.
    """
    url = config.api_url(path)
    headers = _headers(include_auth=include_auth)
    body_bytes = _json.dumps(json_body).encode("utf-8") if json_body is not None else None

    req = _MethodRequest(method, url, data=body_bytes, headers=headers)
    resp = None
    try:
        try:
            resp = _urllib_request.urlopen(req, timeout=timeout)
        except TypeError:
            # very old urllib2 builds have no timeout kwarg on urlopen
            resp = _urllib_request.urlopen(req)
        text = resp.read().decode("utf-8")
        return _handle_response(resp.getcode(), text, url)
    except _urllib_error.HTTPError as exc:
        text = exc.read().decode("utf-8") if exc.fp else ""
        return _handle_response(exc.code, text, url)
    except _urllib_error.URLError as exc:
        raise RevvyApiError("Could not reach REVVY backend at {0}: {1}".format(url, exc))
    except _socket.timeout as exc:
        # On IronPython 2.7's urllib2 port, a raw socket timeout does NOT get
        # wrapped into URLError the way it does under CPython, so it must be
        # caught separately here -- otherwise it propagates as an unhandled
        # exception and crashes the calling pushbutton script instead of
        # surfacing a clean RevvyApiError the caller already knows how to
        # show to the user.
        raise RevvyApiError(
            "REVVY backend at {0} did not respond within {1}s: {2}".format(url, timeout, exc)
        )
    except _socket.error as exc:
        raise RevvyApiError("Could not reach REVVY backend at {0}: {1}".format(url, exc))
    finally:
        if resp is not None:
            resp.close()


def _handle_response(status_code, text, url):
    try:
        payload = _json.loads(text) if text else {}
    except ValueError:
        payload = {"raw": text}

    if status_code in (401, 403):
        # Clear the stored token so the NEXT ensure_authenticated() call
        # re-prompts for login instead of re-sending the same stale/invalid
        # token and failing in a silent loop (config.is_authenticated() only
        # checks presence, not validity).
        config.clear_token()
        raise AuthenticationError(
            "REVVY session expired or invalid. Please log in again.",
            status_code=status_code,
            payload=payload,
        )
    if status_code >= 400:
        detail = payload.get("detail") if isinstance(payload, dict) else None
        raise RevvyApiError(
            "REVVY backend returned {0} for {1}: {2}".format(status_code, url, detail or text),
            status_code=status_code,
            payload=payload,
        )
    return payload


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


def login(email, password):
    """Log in with email/password, store the returned access token, and return it.

    Assumes the standard FastAPI-JWT response shape used elsewhere in this
    project's CLAUDE.md (access token + token_type); if BACKEND-AGENT's
    schema differs, only this function needs to change.
    """
    payload = _request(
        "POST",
        "/auth/login",
        json_body={"email": email, "password": password},
        include_auth=False,
    )
    token = payload.get("access_token")
    if not token:
        raise RevvyApiError("Login response did not include an access_token.", payload=payload)
    config.set_token(token)
    return token


# ---------------------------------------------------------------------------
# Chat Copilot
# ---------------------------------------------------------------------------


def list_chat_sessions():
    return _request("GET", "/chat/sessions")


def create_chat_session(title=None, revit_project_name=None):
    body = {}
    if title:
        body["title"] = title
    if revit_project_name:
        body["revit_project_name"] = revit_project_name
    return _request("POST", "/chat/sessions", json_body=body)


def send_chat_message(session_id, content):
    return _request(
        "POST", "/chat/sessions/{0}/messages".format(session_id), json_body={"content": content}
    )


# ---------------------------------------------------------------------------
# Model Query (read-only)
# ---------------------------------------------------------------------------


def query_model(revit_project_name, query):
    """POST /model/query. Must never be called from inside a Transaction."""
    return _request(
        "POST",
        "/model/query",
        json_body={"revit_project_name": revit_project_name, "query": query},
    )
