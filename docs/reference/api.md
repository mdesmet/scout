---
title: "Local API"
description: "Key endpoints exposed by the loopback-only FastAPI server."
---

The application exposes a local FastAPI API at `http://127.0.0.1:8765`. Interactive OpenAPI
documentation is available at [http://127.0.0.1:8765/docs](http://127.0.0.1:8765/docs) while the
server is running.

| Endpoint | Purpose |
| --- | --- |
| `GET /api/health` | Health, rubric, and capability metadata |
| `/api/runs` | Create and inspect research runs |
| `/api/runs/{id}/events` | Stream run events over SSE |
| `/api/runs/{id}/steer` | Redirect active research |
| `/api/runs/{id}/control/{action}` | Pause, resume, or cancel a run |
| `/api/feedback` | Record explicit feedback |
| `/api/memory` | Inspect and manage learned preferences |
| `/api/profile` | Read and update founder context |
| `/api/learning` | Inspect learning state |

Per-run Markdown, HTML, JSON, and CSV exports are also available through the API.

::: warning
The server is intentionally loopback-only. It is not an authenticated multi-user deployment and
must not be exposed to a broader network.
:::
