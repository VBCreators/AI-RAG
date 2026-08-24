---
name: ci
description: >
  Write, edit, or debug production-grade GitHub Actions workflows and their
  companion files (.pre-commit-config.yaml, dependabot.yml, CODEOWNERS,
  branch protection notes) for a Python/FastAPI + Docker homelab SaaS stack
  deployed via GHCR/Docker Hub + Watchtower. Use this skill whenever the
  user mentions: GitHub Actions, CI pipeline, CI/CD, pre-commit,
  pre-commit-config, workflow file, .github/workflows, GHCR, Docker Hub
  push, image signing, cosign, SBOM, Trivy, Gitleaks, CodeQL, Dependabot,
  branch protection, or Watchtower deployment — even if they only ask for
  "tests" or "security scanning" in CI, or don't explicitly say "GitHub
  Actions." Always load this skill before writing any workflow YAML or
  pre-commit config from memory; the assets/ and references/ here encode
  the security baseline this project requires and should be copied and
  adapted rather than reinvented.
---

# CI Skill: GitHub Actions + Pre-commit for a Python/FastAPI Docker SaaS

This skill produces a **production-grade, security-first CI pipeline** and
the pre-commit configuration that mirrors it locally, for a stack of:
Python/FastAPI, Postgres, MongoDB, Qdrant, Redis, Keycloak, Docker Compose,
GHCR + Docker Hub, Watchtower (CD), Ubuntu, Cloudflare Tunnel.

Guiding rules for anything produced with this skill (see
`references/github-actions-security.md` for the full rationale):

1. Use maintained, popular Actions/hooks — never hand-rolled scanners.
2. Everything free/open-source (GitHub-hosted runners, GHCR, Trivy,
   Gitleaks, OSV-Scanner/pip-audit, CodeQL, Bandit, cosign, syft — all free).
3. Least-privilege `permissions:` on every workflow/job.
4. Every third-party Action must be on the latest version.
5. No long-lived credentials in workflows — use `GITHUB_TOKEN`/OIDC first,
   repo secrets only when a third party (Docker Hub) truly requires it.
6. Fail the build on: lint errors, type errors, test failures, any
   HIGH/CRITICAL vulnerability, any detected secret, any Dockerfile
   best-practice violation flagged by Hadolint at error level.
7. Local pre-commit hooks must mirror CI checks so nothing "only fails in
   CI" — CI re-runs pre-commit in `--all-files` mode as a safety net for
   people who skip/bypass local hooks.

## Directory contents

```
ci/
├── SKILL.md                              # this file
├── scripts/
│   └── validate-workflow.sh              # lints workflow + pre-commit files before you hand them back
├── references/
│   ├── github-actions-security.md        # hardening checklist + rationale (read before writing any workflow)
│   └── pre-commit-best-practices.md      # hook selection + config rationale (read before writing pre-commit config)
└── assets/
    ├── basic-ci.yml                      # full CI workflow template — copy to .github/workflows/ci.yml
    ├── codeql.yml                        # separate CodeQL SAST workflow — copy to .github/workflows/codeql.yml
    ├── pre-commit-config.yaml            # template — copy to repo root as .pre-commit-config.yaml
    └── dependabot.yml                    # template — copy to .github/dependabot.yml
```

## Workflow: how to use this skill

### Step 1 — Understand what needs covering

Ask (or infer from the repo) which of these the project currently has, since
the templates assume all of them and you should trim what's unused:

- FastAPI app with a test suite (pytest)?
- Which of Postgres / MongoDB / Qdrant / Redis does CI need to spin up as
  service containers for integration tests?
- Does the app get built into a Docker image that ships to GHCR and/or
  Docker Hub?
- Is Watchtower already polling a registry, or does the user want a push
  trigger?

### Step 2 — Read the references

Before writing YAML, read:

- `references/github-actions-security.md` — permissions, secrets, action
  pinning, image signing/SBOM, registry auth patterns.
- `references/pre-commit-best-practices.md` — hook set, ordering, CI
  parity, autoupdate cadence.

### Step 3 — Copy and adapt the assets

Copy `assets/basic-ci.yml` to `.github/workflows/ci.yml` in the user's repo
(or hand them the file to place there), `assets/codeql.yml` to
`.github/workflows/codeql.yml`, `assets/pre-commit-config.yaml` to
`.pre-commit-config.yaml`, and `assets/dependabot.yml` to
`.github/dependabot.yml`. Adapt:

- Remove service containers (postgres/mongo/qdrant/redis) the project
  doesn't use.
- Update `IMAGE_NAME`, Python version, and any paths (e.g. if the FastAPI
  app isn't at the repo root).
- Confirm which registries are in play (GHCR only, Docker Hub only, or
  both) and delete the unused push job.

### Step 4 — Tell the user what to configure manually

This skill cannot click buttons in the GitHub UI. Always tell the user to:

- Add repo secrets: `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN` (a Docker Hub
  **access token**, not their password) — only if pushing to Docker Hub.
  GHCR push uses the automatic `GITHUB_TOKEN`, no secret needed.
- Enable branch protection on `main`/`master`: require the `ci` status
  check to pass, require PR review, require signed commits (optional but
  recommended), disallow force-push.
- Enable "Dependabot alerts" and "Dependabot security updates" under repo
  Settings → Security.
- Enable GitHub Advanced Security / code scanning if on a plan that
  supports it (CodeQL still runs and uploads SARIF on free public repos
  and works on private repos with GHAS or the free tier's included
  scanning where applicable — check current GitHub pricing since this
  changes; free for public repos regardless).

### Step 5 — Validate

Run `scripts/validate-workflow.sh <path-to-repo>` (requires `actionlint`
and `yamllint`; the script tells you how to install them if missing) and
fix anything flagged before considering the task done.

### Step 6 — Explain the Watchtower hand-off

CI's job ends at "image pushed to registry, signed, with SBOM attached."
Watchtower (already running in the user's Docker Compose stack) polls the
registry on an interval and redeploys any container whose image changed,
provided the container has the label:

```yaml
labels:
  - "com.centurylinklabs.watchtower.enable=true"
```

No GitHub Actions step is required to "trigger" Watchtower under polling
mode — pushing the new image tag is the trigger. Only add an HTTP-API
notify step (documented in `references/github-actions-security.md`) if the
user specifically wants push-based instant deploys instead of polling.

## When editing an existing workflow instead of creating one

Read the existing file fully first, diagnose the failure/gap against the
checklist in `references/github-actions-security.md`, make the minimal
correct edit, and re-run Step 5's validation. Don't rewrite the whole file
unless it's fundamentally insecure (e.g., no `permissions:` block, secrets
hardcoded, unpinned third-party actions).
