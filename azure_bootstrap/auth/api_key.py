"""API-key header verification helper.

Re-exported from :mod:`azure_bootstrap.security` for ergonomic import. The
canonical pattern for non-webhook FastAPI routes is::

    from azure_bootstrap.auth.api_key import verify_api_key_header, api_key_dependency
    from fastapi import Depends

    # Default (API_KEY env, fail-open when unset):
    @app.get('/api/private', dependencies=[Depends(verify_api_key_header)])
    async def private(): ...

    # Strict / custom env — use the factory so config is not query-injectable:
    @app.get('/api/admin', dependencies=[Depends(api_key_dependency(fail_open_when_unset=False))])
    async def admin(): ...

Webhook routes use :func:`azure_bootstrap.auth.webhook.verify_webhook_client_state`
instead.
"""

from azure_bootstrap.security import api_key_dependency, verify_api_key_header

__all__ = ["api_key_dependency", "verify_api_key_header"]
