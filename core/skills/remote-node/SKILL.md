---
name: remote-node
risk: high
permissions:
  paired_device_required: true
  capability_approval_required: true
  unrestricted_shell: false
  credentials: false
verification_required: true
---
# Remote Node
Remote KRISHNA devices get only explicitly approved capabilities. Pairing never
silently expands the command surface. Host mutation still passes project policy,
shadow repair and verification. Prefer private VPN/SSH transport; do not expose
an unauthenticated KRISHNA control port to the public internet.
