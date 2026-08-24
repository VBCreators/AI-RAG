# Sub-Agents Roster & Delegation Rules

> **When to read this file:**
>
> - Before selecting or delegating to any sub-agent.
> - Whenever the Root Agent needs to decide ownership of a domain task.
> - When resolving conflicts between sub-agents.
>   **Authority:** This file is the authoritative roster. Root `AGENTS.md` takes precedence on security.

---

## Purpose

This file defines the specialized sub-agents available in the repository, their domains, when the Root Agent should delegate to them, and the hand-off contract.

---

## Roster



| Sub-agent ID | Domain                                                            | Primary responsibilities                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | Trigger conditions (delegate when…)                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| ------------ | ----------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `cicd-agent` | Git hygiene, CI/CD pipelines, container registries, Watchtower CD | Owns all Git‑related configuration (`.gitignore`, `.gitattributes`, branch protection, `CODEOWNERS`); manages `pre-commit` hooks (`.pre-commit-config.yaml`); creates and debugs GitHub Actions workflows, issue/PR templates, `dependabot.yml`; designs CI pipelines (lint, type‑check, tests, SAST, secret/container scanning, SBOM, image signing); builds, tags, and pushes Docker images to GHCR or Docker Hub; configures Watchtower polling and labels for automated deployment; proactively updates CI/pre‑commit config when new code, services, or dependencies are added. | User explicitly requests Git repo setup/fix, editing any Git‑related files, creating/modifying pre‑commit hooks, working with anything under `.github/`, designing or troubleshooting a CI pipeline, building/pushing images, or setting up Watchtower; **also** when new application code, a service, or a dependency is introduced – to review and update CI/pre‑commit coverage accordingly. Always uses the `ci` skill for concrete templates and checklists rather than inventing YAML. |
