"""Constant-time comparison + FastAPI API-key helper.

The :func:`compare_secrets` helper centralizes the None/empty/bytes-coercion
dance so call sites can just call it without re-implementing the safe pattern.

The FastAPI API-key helper is fail-open-when-unset by default (matches the
v1 reference behavior); apps that want strict mode pass
``fail_open_when_unset=False``.

**Depends-safety:** ``verify_api_key_header`` exposes only the ``X-API-Key``
header to FastAPI's dependency injector. ``env_var`` / ``fail_open_when_unset``
remain callable kwargs for programmatic use but are NOT request-injectable
(otherwise an attacker could pass ``?env_var=UNSET`` and fail-open past auth).
"""

from __future__ import annotations

import hmac
import inspect
import logging
from typing import Any

_logger = logging.getLogger(__name__)


def compare_secrets(a: str | bytes | None, b: str | bytes | None) -> bool:
    """Constant-time equality. Returns False on any None / empty input.

    Coerces str to bytes via UTF-8. Bytes inputs pass through unchanged.
    """
    if not a or not b:
        return False
    a_b = a.encode("utf-8") if isinstance(a, str) else a
    b_b = b.encode("utf-8") if isinstance(b, str) else b
    return hmac.compare_digest(a_b, b_b)


async def verify_api_key_header(
    x_api_key: str | None = None,
    *,
    env_var: str = "API_KEY",
    fail_open_when_unset: bool = True,
) -> None:
    """FastAPI dependency / programmatic checker. Raises ``HTTPException(401)`` on mismatch.

    When ``fail_open_when_unset`` is True (default) and the env var is unset
    or empty, the check passes — matches the v1 reference behavior. Strict
    mode (env required) is opt-in via ``fail_open_when_unset=False``.

    Prefer::

        @app.get("/private", dependencies=[Depends(verify_api_key_header)])

    or extract the header in the route and ``await verify_api_key_header(x_api_key)``.

    Imports FastAPI lazily so this module is importable without the ``fastapi``
    extra; only callers that actually invoke the function pay the dep.
    """
    import os

    expected = os.environ.get(env_var, "").strip()
    if not expected:
        if fail_open_when_unset:
            return
        from fastapi import HTTPException  # type: ignore[import-not-found]

        raise HTTPException(status_code=401, detail="API key not configured")
    if not compare_secrets(x_api_key, expected):
        _logger.debug(
            "API key validation failed",
            extra={"operation": "verify_api_key_header"},
        )
        from fastapi import HTTPException  # type: ignore[import-not-found]

        raise HTTPException(status_code=401, detail="Unauthorized")


def _harden_api_key_signature_for_fastapi() -> None:
    """Hide config kwargs from FastAPI DI so they cannot be set via query string.

    ``inspect.signature`` (and FastAPI) honor ``__signature__``. The real
    function still accepts ``env_var`` / ``fail_open_when_unset`` for
    programmatic callers.
    """
    try:
        from typing import Annotated

        from fastapi import Header  # type: ignore[import-not-found]
    except ImportError:
        return

    verify_api_key_header.__signature__ = inspect.Signature(  # type: ignore[attr-defined]
        [
            inspect.Parameter(
                "x_api_key",
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                default=None,
                annotation=Annotated[str | None, Header(alias="X-API-Key")],
            )
        ]
    )


_harden_api_key_signature_for_fastapi()


def api_key_dependency(
    *,
    env_var: str = "API_KEY",
    fail_open_when_unset: bool = True,
) -> Any:
    """Return a FastAPI dependency with config closed over (not query-injectable).

    Use when you need a non-default ``env_var`` or ``fail_open_when_unset``::

        @app.get("/admin", dependencies=[Depends(api_key_dependency(fail_open_when_unset=False))])
    """
    try:
        from typing import Annotated

        from fastapi import Header  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "api_key_dependency requires the `fastapi` extra: "
            "pip install azure-bootstrap[fastapi]"
        ) from exc

    async def _dependency(
        x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
    ) -> None:
        await verify_api_key_header(
            x_api_key,
            env_var=env_var,
            fail_open_when_unset=fail_open_when_unset,
        )

    return _dependency


__all__ = ["api_key_dependency", "compare_secrets", "verify_api_key_header"]
