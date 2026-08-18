"""Shared rate limiter for abuse-prone endpoints (register/login).

Uses `slowapi` (a thin wrapper around the `limits` library) with an
in-memory per-process counter keyed by client IP. This is intentionally
simple: it resets on process restart and does not coordinate across
multiple backend replicas. That's an acceptable tradeoff for MVP — if
REVVY is ever deployed with >1 backend replica behind a load balancer,
swap the in-memory storage for a Redis-backed `limits` storage URI
(`Limiter(storage_uri="redis://...")`) without changing call sites.
"""
from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
