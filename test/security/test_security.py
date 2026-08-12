"""Tests for ``azure_bootstrap.security``."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from azure_bootstrap.security import (
    api_key_dependency,
    compare_secrets,
    verify_api_key_header,
)


class TestCompareSecrets:
    def test_match(self) -> None:
        assert compare_secrets("abc", "abc") is True

    def test_mismatch(self) -> None:
        assert compare_secrets("abc", "xyz") is False

    def test_none_left(self) -> None:
        assert compare_secrets(None, "abc") is False

    def test_none_right(self) -> None:
        assert compare_secrets("abc", None) is False

    def test_both_none(self) -> None:
        assert compare_secrets(None, None) is False

    def test_empty(self) -> None:
        assert compare_secrets("", "abc") is False
        assert compare_secrets("abc", "") is False

    def test_bytes_input(self) -> None:
        assert compare_secrets(b"abc", b"abc") is True
        assert compare_secrets("abc", b"abc") is True

    def test_uses_compare_digest(self) -> None:
        source = (
            Path(__file__).parent.parent.parent / "azure_bootstrap" / "security" / "__init__.py"
        )
        text = source.read_text()
        assert "hmac.compare_digest" in text, "compare_secrets must use hmac.compare_digest, not =="


class TestVerifyApiKeyHeader:
    def test_fail_open_when_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("API_KEY", raising=False)
        # Should not raise
        asyncio.run(verify_api_key_header(None))
        asyncio.run(verify_api_key_header("anything"))

    def test_strict_mode_raises_when_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        pytest.importorskip("fastapi")
        from fastapi import HTTPException

        monkeypatch.delenv("API_KEY", raising=False)
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(verify_api_key_header(None, fail_open_when_unset=False))
        assert exc_info.value.status_code == 401

    def test_mismatch_raises_401(self, monkeypatch: pytest.MonkeyPatch) -> None:
        pytest.importorskip("fastapi")
        from fastapi import HTTPException

        monkeypatch.setenv("API_KEY", "expected")
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(verify_api_key_header("wrong"))
        assert exc_info.value.status_code == 401

    def test_match_passes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("API_KEY", "expected")
        # Should not raise:
        asyncio.run(verify_api_key_header("expected"))

    def test_depends_does_not_expose_config_as_query(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Regression: env_var/fail_open must not be attacker-settable via query."""
        pytest.importorskip("fastapi")
        from fastapi import Depends, FastAPI
        from fastapi.testclient import TestClient

        monkeypatch.setenv("API_KEY", "super-secret-key")
        monkeypatch.delenv("THIS_VAR_DOES_NOT_EXIST_XYZ", raising=False)

        app = FastAPI()

        @app.get("/private", dependencies=[Depends(verify_api_key_header)])
        def private() -> dict[str, bool]:
            return {"ok": True}

        client = TestClient(app)
        params = client.app.openapi()["paths"]["/private"]["get"].get("parameters", [])
        names = {p.get("name") for p in params}
        assert "env_var" not in names
        assert "fail_open_when_unset" not in names
        assert any(p.get("in") == "header" and p.get("name") == "X-API-Key" for p in params)

        # Former bypass: ?env_var=<unset>&x_api_key=garbage
        r = client.get(
            "/private",
            params={"x_api_key": "attacker-garbage", "env_var": "THIS_VAR_DOES_NOT_EXIST_XYZ"},
        )
        assert r.status_code == 401

        r = client.get("/private", headers={"X-API-Key": "super-secret-key"})
        assert r.status_code == 200
        assert r.json() == {"ok": True}

    def test_api_key_dependency_strict_factory(self, monkeypatch: pytest.MonkeyPatch) -> None:
        pytest.importorskip("fastapi")
        from fastapi import Depends, FastAPI
        from fastapi.testclient import TestClient

        monkeypatch.delenv("API_KEY", raising=False)
        app = FastAPI()

        @app.get(
            "/strict",
            dependencies=[Depends(api_key_dependency(fail_open_when_unset=False))],
        )
        def strict() -> dict[str, bool]:
            return {"ok": True}

        client = TestClient(app)
        r = client.get("/strict")
        assert r.status_code == 401
