---
name: root-cause-investigation
description: Evidence-first debugging for KRISHNA-managed software projects.
triggers:
  - debug this
  - fix this bug
  - not working
  - error
  - failed
  - root cause
project_scope:
  - "*"
permissions:
  - read_context
  - read_files
  - read_logs
  - shadow_write
risk: medium
verification_required: true
rollback_required: true
---

# Root-cause investigation

Use four phases in order: **investigate -> analyze -> hypothesize -> repair**.

1. Reproduce or observe the failure and capture logs, state and affected components.
2. Identify the smallest plausible fault boundary. Do not edit unrelated files.
3. Rank hypotheses against evidence; distinguish observed facts from inference.
4. Prepare changes in a shadow workspace only.
5. Run the project's registered verification checks.
6. Promote only when every required check passes; otherwise preserve evidence and roll back.

Never report a repair as complete from code inspection alone.
