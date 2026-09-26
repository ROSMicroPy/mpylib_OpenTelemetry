# Documentation website

Eight pages guide readers from the project objective and installation through
configuration, instrumentation, propagation, internals, API signatures, and
troubleshooting. A shared template supplies left-hand navigation, responsive
mobile navigation, and previous/next links. The content works without JavaScript;
JavaScript adds the mobile menu and code-copy controls.

## Build and preview

Requires Python 3.10 or later; no third-party packages or Node build are needed.
From the repository root:

```sh
python3 pages/build.py
python3 pages/check.py
python3 -m http.server 8000 --directory pages/_site
```

Open <http://localhost:8000>. `_site/` is generated and ignored by Git.
The checker validates local links, anchors, page metadata, navigation state,
and syntax of the Python examples; it does not execute board/network examples
or check external links.

## Edit

- `content/*.html`: guide content. Escape `<`, `>` and `&` in code blocks.
- `template.html`: shared page layout.
- `assets/`: stylesheet, progressive enhancement script, favicon.
- `build.py`: page ordering/metadata and API reference generation from `src/`.
- `check.py`: checks run locally and in CI.

Use relative links such as `configuration.html#options`; these work at the root,
at the GitHub project subpath, and in a local preview. Add page slugs to `PAGES`
in the builder. Do not edit `_site/` directly. API signatures and package version
are generated on every build, but prose must be reviewed when behavior changes.

## Enable GitHub Pages once

1. In the GitHub repository, open **Settings → Pages**.
2. Set **Build and deployment → Source** to **GitHub Actions**.
3. Commit and push the documentation and `.github/workflows/pages.yml`.
4. Open **Actions → Documentation Pages** and inspect the deployment result.

The workflow builds and checks every branch push and every pull request. Only
pushes/manual runs on the repository's default branch publish the validated
artifact. A local commit alone cannot trigger GitHub Actions; it must be pushed.
Manual runs are available through **Run workflow**. If an environment protection
rule is configured for `github-pages`, allow deployments from the default branch.

Expected project URL after successful deployment:
<https://rosmicropy.github.io/mpylib_OpenTelemetry/>.
The workflow's deployment environment URL is authoritative, including for forks
or custom domains. Forks should also update repository links in `build.py` and
content. No personal access token or separately maintained `gh-pages` branch is
needed. Only the generated site is uploaded.

Build/validation jobs have read-only repository permissions; deployment has
`pages: write` and `id-token: write`. Pull requests never deploy. A failed check
prevents artifact upload and publication. See GitHub's
[custom Pages workflow documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).
