---
name: verification-gate
description: Independent evidence gate before KRISHNA declares work complete.
triggers:
  - verify
  - check the output
  - test it
  - completed
  - deploy
  - release
project_scope:
  - "*"
permissions:
  - read_context
  - read_files
  - browser_read
risk: low
verification_required: true
rollback_required: true
---

# Verification gate

A completion claim requires observable evidence.

- Prefer registered project checks over ad-hoc confidence.
- For UI work, inspect the real page and collect browser evidence when available.
- For services, verify health plus the affected behavior; HTTP 200 alone is insufficient.
- For generated artifacts, verify the artifact exists, is non-empty and matches the requested reality.
- Use an independent reviewer when practical.
- Failed verification means **not complete** and should trigger rollback or a new investigation.
