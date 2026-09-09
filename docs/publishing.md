---
title: "Publish the documentation"
description: "Preview locally and deploy this site with GitHub Pages."
---

The documentation is a VitePress site built from the repository's `/docs` directory.

## Preview locally

```bash
npm run docs:dev
```

The preview is available at the URL printed by VitePress, normally
[http://127.0.0.1:5173/scout/](http://127.0.0.1:5173/scout/).

## Deploy to GitHub Pages

The workflow at `.github/workflows/docs-pages.yml` builds and deploys the site whenever relevant files
reach `main`. It can also be started manually from the repository's **Actions** tab.

Before the first deployment, open **Settings → Pages** in GitHub and select **GitHub Actions** as the
source. The published site is [https://mdesmet.github.io/scout/](https://mdesmet.github.io/scout/).

::: tip
Run `npm run docs:build` before pushing documentation changes. VitePress reports broken internal links
as build failures.
:::
