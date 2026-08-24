# Pre-commit Best Practices for This Stack

Read this before writing or editing `.pre-commit-config.yaml`. Goal: local
hooks catch everything CI would catch, so red CI runs become rare, and CI
re-runs `pre-commit run --all-files` as a backstop for anyone who commits
with `--no-verify`.

## Hook selection rationale (mirrors `assets/pre-commit-config.yaml`)

| Hook repo | Hook(s) | Why |
|---|---|---|
| `pre-commit/pre-commit-hooks` | `trailing-whitespace`, `end-of-file-fixer`, `check-yaml`, `check-json`, `check-toml`, `check-added-large-files`, `check-merge-conflict`, `check-case-conflict`, `detect-private-key`, `mixed-line-ending` | Battle-tested basic hygiene; `detect-private-key` is a cheap first line of defense against leaking key material |
| `astral-sh/ruff-pre-commit` | `ruff` (lint, `--fix`), `ruff-format` | One fast tool replaces Flake8 + isort + Black; keeps local and CI formatting identical |
| `pre-commit/mirrors-mypy` | `mypy` | Static type-checking; pin `additional_dependencies` to match `requirements`/`pyproject` stubs used |
| `PyCQA/bandit` | `bandit` (`-r`, config from `pyproject.toml`) | Python-specific SAST for common vulns (SQL injection, hardcoded passwords, `eval`, etc.) |
| `pypa/pip-audit` (or `PyCQA/pip-audit-pre-commit` if used) | dependency vuln check | Catches known-CVE dependencies before commit, not just in CI |
| `gitleaks/gitleaks` (via local `gitleaks protect --staged` hook or `pre-commit-gitleaks` mirror) | secret scanning | Same tool as CI, run on the staged diff for instant feedback |
| `hadolint/hadolint` (via `hadolint-docker` hook) | Dockerfile lint | Catches insecure Dockerfile patterns (running as root, missing pinned base image digest, etc.) before it's ever built |
| `koalaman/shellcheck-precommit` | shell script lint | Any `.sh` scripts in `ci/scripts/` or elsewhere get linted too |
| `python-jsonschema/check-jsonschema` | `check-github-workflows` | Validates `.github/workflows/*.yml` against GitHub's official schema — catches typos in workflow YAML before push |
| `commitizen-tools/commitizen` (optional) | conventional-commit message enforcement | Optional but recommended: enables automatic changelog/semver later |

## Ordering & performance

- Put cheap, fast hooks first (`trailing-whitespace`, `check-yaml`) so
  obvious mistakes fail fast before slower hooks (`mypy`, `bandit`) run.
- Use `language: system` sparingly — prefer each hook's own isolated
  environment (the default) so hook dependency versions don't collide with
  the project's own virtualenv.
- Scope expensive hooks with `files:`/`exclude:` regex so they only run
  against relevant paths (e.g., `hadolint` only against `Dockerfile*`).

## Keeping hooks current

- Run `pre-commit autoupdate` on a schedule (weekly is reasonable) and let
  CI's own pre-commit job catch anything that breaks after an update before
  merging the autoupdate PR. Consider a scheduled GitHub Actions workflow
  that runs `pre-commit autoupdate`, commits, and opens a PR automatically
  (using `peter-evans/create-pull-request`) — optional enhancement.
- Pin hook `rev:` to a tag/release, not a branch, same rationale as pinning
  GitHub Actions to a SHA — mutability is the risk being managed.

## CI parity

`assets/basic-ci.yml` includes a dedicated `pre-commit` job that runs:
```yaml
- uses: pre-commit/action@<pinned-sha> # v3.0.1
```
which executes the exact same `.pre-commit-config.yaml` against all files.
This is what catches contributors who bypass local hooks with
`git commit --no-verify` or who haven't installed the hooks at all
(`pre-commit install` should be documented in the repo's `CONTRIBUTING.md`
or `README.md` as a required setup step).

## What NOT to put in pre-commit

- Don't run the full test suite (pytest) in pre-commit by default — it's
  slow and belongs in CI (or as an optional, opt-in local hook for people
  who want it). Fast unit tests only, if any.
- Don't run Trivy image scanning locally in pre-commit — there's no image
  built yet at commit time; that belongs in CI after the Docker build step.
