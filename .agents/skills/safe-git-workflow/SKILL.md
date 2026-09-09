---
name: safe-git-workflow
description: Work safely with Opportunity Scout branches, worktrees, staging, commits, rebases, and pull-request diffs. Use before changing shared work, committing, rebasing, resolving conflicts, or preparing a pull request.
---

# Safe Git workflow

## Establish an isolated workspace

1. Inspect `git status --short`, the current branch, and `git worktree list`.
2. When the main checkout has user changes or concurrent work, create a dedicated worktree and topic
   branch from the intended base.
3. Run Git and project commands with an explicit working directory.
4. Treat files and changes in other worktrees as owned by their author.

## Stage and commit

- Inspect the full status and diff before staging.
- Stage explicit paths only.
- Review `git diff --cached --check` and the staged diff.
- Verify each commit with `git show --name-only --format= HEAD` and `git status --short`.
- Keep each commit buildable, verified, and independently revertible.
- Use `type(scope): outcome`; explain non-obvious rationale, exclusions, and unchanged behavior in the
  body, plus `Closes #<n>` when a tracking issue exists.
- Do not retain development-log commits such as `wip`, `review fix`, or `regenerate`.

## Rebase and review

1. Fetch immediately before rebasing.
2. Rebase onto `origin/main`; never merge `main` into a topic branch.
3. Resolve structured conflicts structurally and validate the result immediately.
4. Inspect both marked conflicts and clean auto-merges for duplicates or silent reversions.
5. Review with `git diff origin/main...HEAD` and compare scope to the issue and PEP.
6. Re-read `git log --oneline origin/main..HEAD`; it should tell the intentional product story.

Never discard work with destructive reset or checkout commands unless the user explicitly requests
that exact operation and the target has been verified.

## Pull-request handoff

Before pushing or creating a pull request, run `verify-change`. The description includes:

- Outcome and motivation.
- PEP and requirement IDs when applicable.
- Compatibility, rollout, privacy, and safety notes when applicable.
- Fresh verification commands and results.
- Explicitly deferred checks with reasons.
