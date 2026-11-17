"""API client tests using a fake session (no network)."""

import asyncio
import importlib.util
import sys
import types
from pathlib import Path

PKG_DIR = Path(__file__).parent.parent / "custom_components" / "dunedin_council"
pkg = types.ModuleType("dc"); pkg.__path__ = [str(PKG_DIR)]; sys.modules["dc"] = pkg
for name in ("const", "api"):
    spec = importlib.util.spec_from_file_location(f"dc.{name}", PKG_DIR / f"{name}.py")
    mod = importlib.util.module_from_spec(spec); sys.modules[f"dc.{name}"] = mod
    spec.loader.exec_module(mod)
api = sys.modules["dc.api"]


class FakeResp:
    def __init__(self, payload): self.payload = payload
    async def __aenter__(self): return self
    async def __aexit__(self, *a): return False
    def raise_for_status(self): pass
    async def json(self, content_type=None): return self.payload


class FakeSession:
    def __init__(self, payload): self.payload, self.calls = payload, []
    def get(self, url, params=None, headers=None):
        self.calls.append((url, params)); return FakeResp(self.payload)


def run(coro): return asyncio.run(coro)


def test_search_builds_escaped_where_clause():
    s = FakeSession({"features": [{"attributes": {"fmtaddress": "5 O'Brien Street Dunedin", "tpklpaprop": 1}}]})
    rows = run(api.async_search_addresses(s, "  5 o'brien   street "))
    assert rows[0]["tpklpaprop"] == 1
    where = s.calls[0][1]["where"]
    assert where == "UPPER(fmtaddress) LIKE '%5 O''BRIEN STREET%'"
    assert s.calls[0][1]["f"] == "json" and s.calls[0][1]["returnGeometry"] == "false"


def test_get_property_uses_integer_id():
    s = FakeSession({"features": [{"attributes": {"numberDay": 3, "CurrentWeek": "b"}}]})
    row = run(api.async_get_property(s, "12345"))
    assert row["numberDay"] == 3
    assert s.calls[0][1]["where"] == "tpklpaprop = 12345"


def test_get_property_rejects_injection_like_ids():
    s = FakeSession({"features": []})
    try:
        run(api.async_get_property(s, "1 OR 1=1"))
        assert False, "should have raised"
    except ValueError:
        pass


def test_empty_result_raises():
    s = FakeSession({"features": []})
    try:
        run(api.async_get_property(s, 99)); assert False
    except api.DunedinApiError:
        pass


def test_arcgis_error_payload_raises():
    s = FakeSession({"error": {"code": 400, "message": "Unable to complete operation."}})
    try:
        run(api.async_search_addresses(s, "x")); assert False
    except api.DunedinApiError:
        pass
