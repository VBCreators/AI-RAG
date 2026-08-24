#!/usr/bin/env bash
#
# ci/scripts/validate-workflow.sh
#
# Deterministic lint pass over GitHub Actions workflows and the
# pre-commit config before handing them back to the user. Run this after
# writing or editing anything in .github/workflows/ or
# .pre-commit-config.yaml.
#
# Usage:
#   ci/scripts/validate-workflow.sh [path-to-repo-root]
#
# Defaults to the current directory if no path is given.

set -euo pipefail

REPO_ROOT="${1:-.}"
cd "$REPO_ROOT"

FAILED=0

info()  { printf '\033[1;34m[info]\033[0m %s\n' "$1"; }
ok()    { printf '\033[1;32m[ok]\033[0m   %s\n' "$1"; }
warn()  { printf '\033[1;33m[warn]\033[0m %s\n' "$1"; }
fail()  { printf '\033[1;31m[fail]\033[0m %s\n' "$1"; FAILED=1; }

echo "=== Validating CI/pre-commit config in: $(pwd) ==="
echo

# ---------------------------------------------------------------------
# 1. yamllint over all workflow + config YAML
# ---------------------------------------------------------------------
if command -v yamllint >/dev/null 2>&1; then
  info "Running yamllint..."
  YAML_TARGETS=()
  [ -d .github/workflows ] && YAML_TARGETS+=(.github/workflows)
  [ -f .pre-commit-config.yaml ] && YAML_TARGETS+=(.pre-commit-config.yaml)
  [ -f .github/dependabot.yml ] && YAML_TARGETS+=(.github/dependabot.yml)
  if [ "${#YAML_TARGETS[@]}" -gt 0 ]; then
    if yamllint -d "{extends: default, rules: {line-length: {max: 120}}}" "${YAML_TARGETS[@]}"; then
      ok "yamllint passed"
    else
      fail "yamllint found issues (see above)"
    fi
  else
    warn "No workflow/pre-commit YAML found to lint"
  fi
else
  warn "yamllint not installed - skipping. Install with: pip install yamllint"
fi
echo

# ---------------------------------------------------------------------
# 2. actionlint over all workflow files (catches GitHub Actions-specific
#    mistakes yamllint can't: bad expressions, invalid contexts, shell
#    issues inside run: blocks via embedded shellcheck, etc.)
# ---------------------------------------------------------------------
if command -v actionlint >/dev/null 2>&1; then
  info "Running actionlint..."
  if [ -d .github/workflows ]; then
    if actionlint; then
      ok "actionlint passed"
    else
      fail "actionlint found issues (see above)"
    fi
  else
    warn "No .github/workflows directory found"
  fi
else
  warn "actionlint not installed - skipping. Install with:"
  warn "  go install github.com/rhysd/actionlint/cmd/actionlint@latest"
  warn "  (or: brew install actionlint / see https://github.com/rhysd/actionlint#installation)"
fi
echo

# ---------------------------------------------------------------------
# 3. Confirm every third-party action reference is pinned to a full SHA,
#    not a mutable tag or branch. This is a required security control -
#    treat any hit here as a failure, not a warning.
# ---------------------------------------------------------------------
if [ -d .github/workflows ]; then
  info "Checking that third-party actions are pinned to a commit SHA..."
  UNPINNED_FOUND=0
  while IFS= read -r line; do
    file="${line%%:*}"
    rest="${line#*:}"
    lineno="${rest%%:*}"
    content="${rest#*:}"
    # Pull out the ref after the last '@' on the "uses:" line
    ref="${content##*@}"
    ref="${ref%%#*}"
    ref="$(echo "$ref" | tr -d '[:space:]' | tr -d '"'"'"'')"
    # Local actions (./) and docker:// refs are exempt from SHA pinning
    if [[ "$content" == *"uses: ./"* || "$content" == *"uses: docker://"* ]]; then
      continue
    fi
    if [[ ! "$ref" =~ ^[0-9a-f]{40}$ ]]; then
      fail "$file:$lineno not pinned to a 40-char commit SHA -> $(echo "$content" | sed 's/^ *//')"
      UNPINNED_FOUND=1
    fi
  done < <(grep -rEn '^\s*uses:\s*[^$]' --include='*.yml' --include='*.yaml' .github/workflows 2>/dev/null || true)

  if [ "$UNPINNED_FOUND" -eq 0 ]; then
    ok "All third-party actions appear to be pinned to a commit SHA"
  else
    echo "See ci/references/github-actions-security.md rule #2."
  fi
fi
echo

# ---------------------------------------------------------------------
# 4. Confirm every workflow declares an explicit `permissions:` block
#    (top-level). Missing this is a common over-privilege mistake.
# ---------------------------------------------------------------------
if [ -d .github/workflows ]; then
  info "Checking that every workflow sets a top-level 'permissions:' block..."
  for f in .github/workflows/*.yml .github/workflows/*.yaml; do
    [ -e "$f" ] || continue
    if ! grep -qE '^permissions:' "$f"; then
      fail "$f has no top-level 'permissions:' block (defaults are overly broad)"
    fi
  done
  [ "$FAILED" -eq 0 ] && ok "All checked workflows declare 'permissions:'"
fi
echo

# ---------------------------------------------------------------------
# 5. Run pre-commit itself against all files, if installed and a config
#    exists (this is the most thorough check, since it exercises every
#    hook - lint, type-check, secrets, Dockerfile lint, etc.)
# ---------------------------------------------------------------------
if [ -f .pre-commit-config.yaml ]; then
  if command -v pre-commit >/dev/null 2>&1; then
    info "Running 'pre-commit run --all-files' (this can take a while the first time)..."
    if pre-commit run --all-files; then
      ok "pre-commit hooks passed"
    else
      fail "pre-commit hooks reported issues (see above)"
    fi
  else
    warn "pre-commit not installed - skipping. Install with: pip install pre-commit"
  fi
else
  warn "No .pre-commit-config.yaml found at repo root"
fi
echo

echo "=== Validation summary ==="
if [ "$FAILED" -eq 0 ]; then
  ok "All checks passed (or were skipped due to missing tools - install them for full coverage)."
  exit 0
else
  fail "One or more checks failed. Fix the issues above before handing this back to the user."
  exit 1
fi
