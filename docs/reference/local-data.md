---
title: "Local data and privacy"
description: "Where Opportunity Scout stores research artifacts and what remains private."
---

SQLite data and research artifacts live in `data/`, which is ignored by Git. Set `SCOUT_DATA_DIR` to
use a different local location.

Each run can contain founder context, memory snapshots, feedback, sources, prompts, model responses,
Codex events and logs, checkpoints, reports, and exports. These artifacts stay local unless you
explicitly export or publish them.

## Privacy boundaries

- Research workers use isolated, read-only CLI sessions with public web search.
- User configuration, hooks, plugins, connected apps, shell tools, and browser automation are not
  available to research workers.
- The application does not schedule outreach, scrape private accounts, or make purchases.
- Synthetic examples are labeled and cannot feed learning or customer outcomes.
- The server binds to `127.0.0.1` and rejects foreign-origin mutations.

::: info
Exports may contain founder context and research evidence. Review them before sharing.
:::
