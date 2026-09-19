---
name: autonomous-operator
version: 1
risk: high
projects: [krishna, kuber, youtube-ai]
permissions:
  observe_registered_projects: true
  mutate_only_allowlisted_actions: true
  shadow_workspace_required: true
  raw_unscoped_shell: false
  credentials: false
verification_required: true
rollback_required: true
---
# Autonomous Operator
KRISHNA may continuously observe explicitly registered projects. A failure becomes
an incident, not permission to edit. Root-cause investigation precedes repair.
Repairs run only through a project allowlisted action in a shadow workspace.
Verification must pass before promotion. Failed verification is rejected and the
working project remains unchanged. Only verified outcomes may enter Project Brain.
