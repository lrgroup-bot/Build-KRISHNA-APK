# KRISHNA Core

Local PC authority for KRISHNA Mobile.

KRISHNA is designed as a persistent autonomous software intelligence:

Observe -> Understand -> Investigate -> Research -> Plan -> Change Gate -> Shadow Execute -> Test -> Verify -> Learn.

## Core capabilities

- secure gateway/API
- persistent project + incident memory
- Project Graph for component/dependency relationships
- Evidence Engine with registered safe probes
- hypothesis-based Investigation Engine
- Knowledge Ingestor for text/webpage/document content
- local/cloud model router
- health watcher with state transitions
- verification gates
- policy-driven recovery ladder
- defensive static-security scanner
- KRISHNA Vision for explicitly enrolled local identities
- audit log

## Mythos Engineering Stack

The engineering stack integrates capability patterns researched from:

- mythos-agent/mythos-agent — recon, hypothesis, defensive analysis, confidence/verification
- SWE-agent/mini-swe-agent — minimal linear engineering loop
- SWE-agent/SWE-ReX — sandboxed execution pattern
- DeusData/codebase-memory-mcp — repository graph and impact intelligence
- Eilodon/CALM — hard pre-write safety gates and blast-radius review
- FARD-Lab/ARISE — Python data-flow slicing/fault localization
- trycua/cua — computer/browser operator layer
- aaif-goose/goose — provider/MCP extension architecture

External repositories are not copied wholesale into KRISHNA. They remain optional, replaceable adapters so KRISHNA keeps ownership of policy, memory, identity, audit and verification.

### Engineering API

- GET /api/engineering/status
- GET /api/engineering/operator/status
- POST /api/engineering/recon
- POST /api/engineering/change-gate
- POST /api/engineering/shadow-plan
- POST /api/engineering/operator/diagnostic

### Change gate

High-risk writes are blocked unless required evidence is present. The gate considers:

- stale file hash
- caller/fan-in count
- sensitive file category
- patch size
- test evidence
- external graph risk
- explicit confirmation for high-risk changes

### Shadow worker

KRISHNA does not translate arbitrary natural language directly into shell commands. The engineering worker accepts an explicit argv plan and executes only allowlisted developer tools inside a disposable shadow workspace.

The current local shadow backend can later be replaced by SWE-ReX without changing the KRISHNA orchestration API.

## Safety model

Natural-language input cannot directly execute arbitrary shell commands.
State-changing recovery operations require pre-registered actions and the KRISHNA_ALLOW_ACTIONS policy flag.
Security scanning is defensive and intended only for KRISHNA-owned or explicitly authorized projects.
KRISHNA must not report work as completed merely because code changed; completion requires verification evidence.
High-risk code changes require a change-gate pass and shadow verification before deployment.

Secrets stay outside Git in environment variables or local config.
