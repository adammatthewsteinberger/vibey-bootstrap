# azure-bootstrap

> The cross-cutting layer for Azure Functions, FastAPI services, and AKS workers.
> One call bootstraps logging → App Configuration + Key Vault → Application Insights
> and hands you a populated `os.environ`. Everything past that (alerts, tracing,
> Service Bus, ten log transports, a scaffold CLI) is opt-in via pip extras.
> Used across 17+ Azure Functions repos at Vizius.

[![PyPI](https://img.shields.io/pypi/v/azure-bootstrap.svg)](https://pypi.org/project/azure-bootstrap/)
[![Downloads](https://img.shields.io/pypi/dm/azure-bootstrap.svg)](https://pypi.org/project/azure-bootstrap/)
[![Python](https://img.shields.io/pypi/pyversions/azure-bootstrap.svg)](https://pypi.org/project/azure-bootstrap/)
[![CI/CD](https://github.com/TheViziusGroup/azure-bootstrap/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/TheViziusGroup/azure-bootstrap/actions/workflows/ci-cd.yml)
[![Docs](https://img.shields.io/badge/docs-github.io-blue.svg)](https://theviziusgroup.github.io/azure-bootstrap/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/TheViziusGroup/azure-bootstrap/blob/main/LICENSE)

## Why

Every Azure app hits the same startup deadlock: you need logging to report
config loading, but App Insights logging needs config to initialize. Most repos
solve it with a copy-pasted `src/infrastructure/` folder that drifts. This
library is that folder, done once, tested, and versioned.

The **four-phase bootstrap** breaks the cycle:

1. **Console logging** — works immediately, before anything loads.
2. **Telemetry from env** — App Insights if `APPLICATIONINSIGHTS_CONNECTION_STRING` is already set.
3. **Configuration** — Azure App Configuration + Key Vault references → `os.environ`.
   Local values (`local.settings.json`, your shell) always win; nothing is overwritten.
4. **Telemetry upgrade** — if the connection string only arrived via config, upgrade now.

Guarantees: the v1 surface is preserved byte-identical across v2 and v3; every
extra is opt-in and most are stdlib-only; log transports never block, never raise,
and use a bounded buffer. `USE_MOCK_BOOTSTRAP=true` runs everything without Azure.

## Quick start

```bash
pip install azure-bootstrap
```

```python
import os
from azure_bootstrap import initialize_application, get_bootstrap_logger

logger = get_bootstrap_logger(__name__)   # usable before bootstrap completes
config_repo = initialize_application()     # runs all four phases

db_host = os.getenv("DATABASE_HOST")       # App Config + Key Vault values are in os.environ
```

Requires Python 3.11+. Falls back to plain environment variables when App
Configuration is not configured, so the same code runs locally and in Azure.

## Worked example: production-grade logging in four lines

```python
from azure_bootstrap.alerts import install_global_exception_hooks, register_dispatcher
from azure_bootstrap.bootstrap import ensure_bootstrap
from azure_bootstrap.logging import configure_logging


def my_email_sender(recipients, subject, html_body):
    ...  # any callable with this signature (Graph, SendGrid, ACS)


configure_logging()
install_global_exception_hooks()
ensure_bootstrap()
register_dispatcher(my_email_sender, recipients=["dev-alerts@example.com"])
```

After this, every line emitted through stdlib `logging` carries a correlation
ID, extra fields render as greppable `key=repr(value)` pairs, noisy third-party
loggers are silenced, and uncaught exceptions fire CRITICAL alerts with dedup,
rate-limiting, and escalation. Runnable version:
[examples/01_quickstart.py](https://github.com/TheViziusGroup/azure-bootstrap/blob/main/examples/01_quickstart.py).

## What's in the box

| Layer | Install | You get |
| --- | --- | --- |
| **v1 core** | `azure-bootstrap` | Four-phase bootstrap, `EnhancedConfigRepository`, `TelemetryManager` |
| **v2 Tier 1** (always on, stdlib) | `azure-bootstrap` | Structured logging, correlation IDs, masking, `@traced`, counters, error vocabulary, soft-fail, phases, validation, path safety, fail-close env helpers |
| **v2 Tier 2/3** (opt-in) | `[alerts]`, `[fastapi]`, `[servicebus]`, `[retry]`, … | Tiered alerts, FastAPI middleware, health probes, heartbeat, Service Bus consumer + DLQ, webhook auth, ingress hardening, HMAC tokens, AI usage tracker |
| **v3** (opt-in) | `[logging-all]`, `[db]`, `[email]`, `[http]`, `[aks]`, … | Ten log transports, SQLAlchemy + outbox, ACS email, hardened HTTP client, DocumentDB factory, AKS runtime helpers, governance, `azbootstrap` scaffold CLI |

```bash
# Common combinations
pip install 'azure-bootstrap[alerts,fastapi,health]'
pip install 'azure-bootstrap[servicebus,sb-lock,retry,heartbeat]'
pip install 'azure-bootstrap[all]'
```

The full extras matrix (40+ extras, what each pulls in, when you need it) is in
the [Usage Guide](https://theviziusgroup.github.io/azure-bootstrap/usage/#1-installation-extras).

<details>
<summary>Feature inventory by release</summary>

**v2** — structured logging (`ExtraFieldsFormatter`, `correlation_scope`,
secret/email/control-char masking, noisy-logger silencing) · `@traced` with
latency histograms and slow-budget alerts · `alert_dev_team` with WARN / ERROR /
CRITICAL, dedup + rate-limit + escalation, `install_global_exception_hooks` ·
`PipelineError` → `UnrecoverableError` / `TransientError` with `is_unrecoverable`,
soft-fail and per-phase guards · 4-gate attachment classifier (extension → MIME →
size → magic bytes), zip-bomb defense, PDF action stripping, filename sanitizer +
root confinement · Service Bus `handle_message` with dead-letter-vs-abandon
routing and `lock_for_process` · `install_graph_webhook_route` with validation
handshake, clientState verification, dedup, rate limit · AI usage tracker (tokens
+ cost, sliding windows, soft TPM cap) · health probes, FastAPI middleware,
heartbeat + consumer watchdog, dynamic log-level refresh, DLQ digest with
HMAC-signed resubmit tokens, `/api/metrics` aggregator.

**v3** — ten logging transports (console, App Insights, Sumo Logic, Panther, file,
blob, SQL, NoSQL, ADX, Event Hubs; all share `_BufferedShipper` guarantees) ·
SQLAlchemy session factory, Alembic helpers, transactional outbox · `AcsEmailSender`
· hardened sync `requests` session + optional async `httpx` · Mongo/Cosmos client
factory from env · AKS `build_info`, SIGTERM handlers, leader-election stub ·
budget guard + usage tracking hooks · `azbootstrap list|scaffold` for
Terraform/Bicep/Helm/GitOps/CI/policy templates.

Every entry is cataloged by tier in the
[CHANGELOG](https://github.com/TheViziusGroup/azure-bootstrap/blob/main/CHANGELOG.md).

</details>

## Examples

[examples/](https://github.com/TheViziusGroup/azure-bootstrap/tree/main/examples/)
holds 46 numbered single-concept files plus 3 end-to-end app templates. Every
file runs with `USE_MOCK_BOOTSTRAP=true` and ends with an `# ── Expected output ──`
block. Start with:

| File | Concept |
| --- | --- |
| [01_quickstart.py](https://github.com/TheViziusGroup/azure-bootstrap/blob/main/examples/01_quickstart.py) | 30-second setup |
| [03_correlation_scope.py](https://github.com/TheViziusGroup/azure-bootstrap/blob/main/examples/03_correlation_scope.py) | Correlation IDs across nested calls |
| [09_soft_fail.py](https://github.com/TheViziusGroup/azure-bootstrap/blob/main/examples/09_soft_fail.py) | Degraded-result pattern |
| [21_consumer_wrapper.py](https://github.com/TheViziusGroup/azure-bootstrap/blob/main/examples/21_consumer_wrapper.py) | Service Bus handler |
| [39_v3_transports.py](https://github.com/TheViziusGroup/azure-bootstrap/blob/main/examples/39_v3_transports.py) | All ten log sinks |
| [e2e_azure_function.py](https://github.com/TheViziusGroup/azure-bootstrap/blob/main/examples/e2e_azure_function.py) | Full Azure Function |
| [e2e_fastapi_pipeline.py](https://github.com/TheViziusGroup/azure-bootstrap/blob/main/examples/e2e_fastapi_pipeline.py) | Full FastAPI app |
| [e2e_aks_sb_worker.py](https://github.com/TheViziusGroup/azure-bootstrap/blob/main/examples/e2e_aks_sb_worker.py) | Full AKS Service Bus consumer |

Reading order and per-example extras:
[examples/README.md](https://github.com/TheViziusGroup/azure-bootstrap/blob/main/examples/README.md).

## Docs & links

- **[Documentation site](https://theviziusgroup.github.io/azure-bootstrap/)** — usage guide, migration guides, generated API reference for all 45 public packages
- **[Usage Guide](https://theviziusgroup.github.io/azure-bootstrap/usage/)** — installation & extras matrix, every subpackage, three end-to-end recipes, TypeScript/Next.js integration
- **[API Reference](https://theviziusgroup.github.io/azure-bootstrap/reference/)** — rendered from docstrings and signatures on every push
- **[CHANGELOG](https://github.com/TheViziusGroup/azure-bootstrap/blob/main/CHANGELOG.md)** · **[v1 → v2](https://github.com/TheViziusGroup/azure-bootstrap/blob/main/MIGRATING-FROM-V1.md)** · **[v2 → v3](https://github.com/TheViziusGroup/azure-bootstrap/blob/main/MIGRATING-TO-V3.md)** (additive; pin `azure-bootstrap>=3.0,<4`)
- **[PyPI](https://pypi.org/project/azure-bootstrap/)** · **[Issues](https://github.com/adammatthewsteinberger/azure-bootstrap/issues)** · **[Security policy](https://github.com/adammatthewsteinberger/azure-bootstrap/security/policy)**

## Related projects

Part of the same open-source family — MIT, on PyPI:

- **[claudeloop](https://github.com/adammatthewsteinberger/claudeloop)** · **[codexloop](https://github.com/adammatthewsteinberger/codexloop)** · **[cursorloop](https://github.com/adammatthewsteinberger/cursorloop)** · **[agyloop](https://github.com/adammatthewsteinberger/agyloop)** — autonomous coding-session runners with the same contract, different vendor
- **[vibey](https://github.com/adammatthewsteinberger/vibey)** — six-phase queue conductor over the loop runners
- **[vibe-engineering-skills](https://github.com/adammatthewsteinberger/vibe-engineering-skills)** — Claude Code plugin marketplace: 18 plugins / 71 Agent Skills (includes an `azure-bootstrap` plugin)
- **[homebrew-tap](https://github.com/adammatthewsteinberger/homebrew-tap)** — `brew tap adammatthewsteinberger/tap`
- **[clippy-pet](https://github.com/adammatthewsteinberger/clippy-pet)** — the fun one

## Contributing

```bash
git clone https://github.com/adammatthewsteinberger/azure-bootstrap
cd azure-bootstrap
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,test,all]"
pytest -m "not integration"          # unit suite with coverage
```

Branch from `develop`, Conventional Commits, PRs need green CI (unit + integration
+ docs build). Coverage floor is 85% (90% for new code). Details in
[CONTRIBUTING.md](https://github.com/TheViziusGroup/azure-bootstrap/blob/main/CONTRIBUTING.md);
AI-assistant context lives in
[CLAUDE.md](https://github.com/TheViziusGroup/azure-bootstrap/blob/main/CLAUDE.md).

## License

MIT — see [LICENSE](https://github.com/TheViziusGroup/azure-bootstrap/blob/main/LICENSE).

---

Built by [Adam Matthew Steinberger](https://hire.adam.matthewsteinberger.com) · [more open source](https://hire.adam.matthewsteinberger.com/open-source)
