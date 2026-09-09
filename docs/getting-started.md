---
title: "Getting started"
description: "Install Opportunity Scout and run the local workspace."
---

## Requirements

- Python 3.10 or newer
- Node.js 22.12+ or Node.js 20.19+
- An authenticated Codex CLI supporting `exec --output-schema`, `--ephemeral`, and
  `--ignore-user-config`

### 1. Clone and enter the repository

```bash
git clone https://github.com/mdesmet/scout.git
cd scout
```

### 2. Install dependencies

```bash
./setup.sh
```

### 3. Authenticate Codex

```bash
codex login
```

Skip this step if the CLI is already authenticated.

### 4. Start the workspace

```bash
./start.sh
```

### 5. Open Opportunity Scout

Visit [http://127.0.0.1:8765](http://127.0.0.1:8765).

## Start a research run

1. Add keywords describing a market, workflow, or problem space.
2. Optionally add founder context such as skills, customer access, geography, time, and budget.
3. Choose a research horizon and opportunity limit.
4. Start the scout and follow progress in the research trail.

The default run uses a 90-day discovery window, returns up to five opportunities, and allows up to
20 minutes of research. Research consumes your account's Codex allowance.

::: warning
Run one server worker. Do not use Uvicorn `--workers` or development reload while research is active.
:::

## Development commands

```bash Backend
.venv/bin/python -m uvicorn scout.app:app --host 127.0.0.1 --port 8765
```

```bash Frontend
npm run dev
```

```bash Backend tests
.venv/bin/python -m pytest -q
```

```bash Production build
npm run build
```

```bash Browser tests
npm test
```
