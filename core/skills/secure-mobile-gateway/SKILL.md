---
name: secure-mobile-gateway
version: 1
risk: high
projects: [krishna]
permissions:
  mobile_chat: true
  device_pairing: true
  raw_shell: false
  credentials: false
  host_filesystem: false
verification_required: true
rollback_required: true
---
# KRISHNA Secure Mobile Gateway

KRISHNA Mobile is a conversation interface, not an administrator dashboard.

Use gateway-owned pairing: a new device creates a short-lived pending request;
PC-side approval issues a fresh high-entropy token; only the token hash is persisted.
Re-pairing rotates credentials. Unknown devices receive no KRISHNA RPC access.

Expose only narrow RPC methods for chat, project conversation, project creation and
safe status summaries. Never expose raw shell, arbitrary filesystem, secret retrieval,
permission changes, verification bypass, or unrestricted host RPC to mobile.

Any request that causes project/system changes is still governed by KRISHNA Core,
skill permissions, verification and rollback.
