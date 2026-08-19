# GitHub Actions Security Hardening Checklist

Read this before writing or editing any file in `.github/workflows/`.
Every point below is a hard requirement for this project, not a suggestion,
unless marked "optional."

## 1. Least-privilege `permissions:`

Set a repo-wide default of `permissions: {}` is not possible via workflow
file, but you can and must set an explicit, minimal `permissions:` block at
the **workflow level**, and tighten further at the **job level** for jobs
that need more (e.g. `id-token: write` only on the job that pushes/signs
images):

```yaml
permissions:
  contents: read
```

Then per-job overrides, e.g. for a job that pushes packages and needs OIDC:

```yaml
jobs:
  build-and-push:
    permissions:
      contents: read
      packages: write       # push to GHCR
      id-token: write       # OIDC for cosign keyless signing
      security-events: write # upload SARIF (CodeQL/Trivy)
```

Never leave `permissions:` unset — the default token permissions are
broader than almost any job needs and are a common supply-chain attack
vector (a compromised dependency in a build step could otherwise write to
the repo, releases, etc.).

## 2. Pin every third-party Action to a full commit SHA

Tags (`@v4`) and branches are mutable and can be repointed by a compromised
or malicious maintainer/account. Pin to the full 40-character SHA and leave
the human-readable version as a trailing comment:

```yaml
- uses: actions/checkout@8410ad0602e1e429cee44a835ae9f77f654a6694 # v5.0.0
```

Actions published by `actions/*` and `github/*` are lower risk but should
still be pinned — treat this as non-negotiable for every third-party
action. Let **Dependabot** keep these SHAs current safely (see
`assets/dependabot.yml`, which includes a `github-actions` ecosystem entry
that bumps pinned SHAs via PRs you review).

## 3. Never hardcode credentials; prefer OIDC / `GITHUB_TOKEN`

- Pushing to **GHCR** from the same repo: use the automatically-injected
  `GITHUB_TOKEN` — no PAT, no long-lived secret needed.
  ```yaml
  - uses: docker/login-action@<pinned-sha> # v3
    with:
      registry: ghcr.io
      username: ${{ github.actor }}
      password: ${{ secrets.GITHUB_TOKEN }}
  ```
- Pushing to **Docker Hub**: Docker Hub doesn't support GitHub OIDC
  federation, so a secret is unavoidable — use a **Docker Hub access
  token** (scoped, revocable) stored as `DOCKERHUB_TOKEN`, never the
  account password.
- **cosign keyless signing**: use OIDC (`id-token: write` permission) via
  Sigstore's Fulcio/Rekor instead of managing a private signing key —
  free, no key material to leak.

## 4. Trigger hygiene — avoid `pull_request_target` foot-guns

- Use `pull_request` (not `pull_request_target`) for anything that checks
  out and runs untrusted fork code (lint/test on PRs). `pull_request_target`
  runs with write-level secrets against the base branch's workflow file but
  can be tricked into checking out and executing attacker-controlled code —
  only use it when you specifically need to comment on/label PRs from
  forks, and never check out the PR head SHA with it in a job that also
  has secrets.
- Never trust `github.event.pull_request.title`,
  `github.head_ref`, or other user-controllable strings by interpolating
  them directly into `run:` shell steps (`run: echo "${{ github.event.
  pull_request.title }}"` is a script-injection vector). Pass them through
  `env:` first:
  ```yaml
  - run: echo "$PR_TITLE"
    env:
      PR_TITLE: ${{ github.event.pull_request.title }}
  ```

## 5. Required scan types (all free/OSS, all fail the build on findings)

| Concern | Tool | Notes |
|---|---|---|
| Python lint + format | Ruff | Fast, replaces flake8+isort+black-check |
| Python type-check | mypy (or pyright) | Run in strict-ish mode |
| Python SAST | Bandit | Flags common Python security anti-patterns |
| Python dependency vulns | pip-audit (or OSV-Scanner) | Checks against OSV/PyPI advisory DB |
| Secret scanning | Gitleaks | Scans diff + full history option |
| Container/image + filesystem vulns | Trivy | Scans image layers, OS packages, and `requirements.txt`/lockfiles |
| Dockerfile lint | Hadolint | Best-practice/security lint for Dockerfiles |
| Code SAST (deeper, multi-language) | CodeQL | GitHub-native, free for public repos, free/GHAS-tier for private |
| SBOM | Syft (via `anchore/sbom-action`) | Generates CycloneDX/SPDX, attach to release/image |
| Image signing | cosign (Sigstore, keyless) | Signs the pushed digest; verify in CD if desired |

All of these are wired into `assets/basic-ci.yml`; `codeql.yml` is split
out since it runs on its own schedule/trigger pattern.

## 6. Secrets in the repo, not in workflows

Store all credentials in **GitHub repo/org Settings → Secrets and
variables → Actions**. Never commit `.env` files with real values — commit
`.env.example` only, and make sure `.gitignore` excludes real `.env`
files (see the `.gitignore`/`gitignore` pre-commit hook that catches
accidental commits, and Gitleaks as the CI backstop).

## 7. Branch protection (configure in GitHub UI/`gh` CLI, not YAML)

- Require the `ci` (and `codeql`) status checks to pass before merge.
- Require at least 1 approving review (even solo — use a second account
  or, more practically, treat this as a checklist item for team growth).
- Require branches to be up to date before merging.
- Require signed commits (optional but recommended — pairs with
  `pre-commit`'s `sign-off` conventions).
- Disallow force-pushes and branch deletion on `main`.
- Restrict who can push directly to `main` (PR-only).

If the `gh` CLI is authenticated and available, this can be scripted:
```bash
gh api -X PUT repos/<owner>/<repo>/branches/main/protection \
  -F required_status_checks[strict]=true \
  -F "required_status_checks[contexts][]=ci" \
  -F enforce_admins=true \
  -F required_pull_request_reviews[required_approving_review_count]=1 \
  -F restrictions=null
```

## 8. Image tagging & provenance

- Tag pushed images with: `sha-<short-commit-sha>` (always),
  `<semver>` (on tagged releases), and `latest` (only on the default
  branch, never on PR builds).
- Use `docker/build-push-action` with `provenance: true` and
  `sbom: true` (Buildx-native attestations) in addition to the explicit
  Syft SBOM step, for defense in depth.
- Multi-arch (`linux/amd64,linux/arm64`) via Buildx/QEMU only if the
  homelab actually needs arm64; otherwise build `linux/amd64` only to
  save CI minutes.

## 9. Watchtower push-trigger (optional, only if not polling)

If the user wants instant deploys instead of Watchtower's default polling
interval, Watchtower can expose an HTTP API
(`WATCHTOWER_HTTP_API_UPDATE=true` + `WATCHTOWER_HTTP_API_TOKEN`) that a
final CI/CD step calls after a successful push, over the **Cloudflare
Tunnel** hostname already fronting the homelab (never expose the
Watchtower API port directly to the internet):

```yaml
- name: Trigger Watchtower update
  run: |
    curl -fsSL -X POST \
      -H "Authorization: Bearer ${{ secrets.WATCHTOWER_HTTP_API_TOKEN }}" \
      "https://watchtower.<your-cloudflare-tunnel-hostname>/v1/update"
```
Store `WATCHTOWER_HTTP_API_TOKEN` as a repo secret; never hardcode it. By
default, prefer plain polling — it's simpler, needs no exposed endpoint,
and no secret to leak.

## 10. Staging vs. production

- Use **GitHub Environments** (`environment: staging` / `environment:
  production`) with required reviewers on the `production` environment so
  a human approves before an image tagged for prod is pushed/deployed.
  Environment-scoped secrets keep prod credentials separate from staging.
