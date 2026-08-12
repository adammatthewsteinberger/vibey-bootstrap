"""Webhook + API-key authentication helpers."""

from azure_bootstrap.auth.api_key import api_key_dependency, verify_api_key_header
from azure_bootstrap.auth.hmac import verify_hmac_signature
from azure_bootstrap.auth.webhook import (
    WebhookDedup,
    install_graph_webhook_route,
    validation_token_handshake,
    verify_webhook_client_state,
)

__all__ = [
    "WebhookDedup",
    "api_key_dependency",
    "install_graph_webhook_route",
    "validation_token_handshake",
    "verify_api_key_header",
    "verify_hmac_signature",
    "verify_webhook_client_state",
]
