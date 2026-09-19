# KRISHNA Core

Local PC authority for KRISHNA Mobile.

KRISHNA is designed as a persistent autonomous software intelligence:

Observe -> Understand -> Investigate -> Research -> Plan -> Act -> Shadow Test -> Verify -> Review -> Learn.

## Implemented intelligence layers

- secure gateway/API
- persistent project + incident memory
- registered-project policy with local/restricted/cloud privacy profiles
- Repository Indexer for local code structure, hashes, imports and Python symbols
- Project Graph for component/file/dependency relationships
- Evidence Engine with registered safe probes
- local evidence collectors for project files, recent logs, dependency manifests and registered endpoints
- hypothesis-based Investigation Engine
- Knowledge Ingestor for text/webpage/document content
- registered Action Registry (natural language is never converted directly to shell)
- disposable Shadow Workspace for non-production repair testing
- evidence-first Shadow Repair Agent
- mandatory Verification Engine
- second-pass Verification Reviewer that reports whether the reviewer is actually provider-independent
- CPU/RAM/concurrency Resource Governor policy
- privacy-aware local/cloud model routing
- policy-driven autonomous recovery ladder
- defensive static-security scanner
- watcher health transitions
- rollback-ready audit and incident history

## Project privacy

Registered projects can use:

- `local_only` - project context stays on the local model; cloud fallback is blocked.
- `restricted` - same cloud block, intended for especially sensitive projects.
- `approved_cloud` - local model is tried first and cloud fallback may be used.

Sensitive projects such as Trinetra should be registered as `restricted`.

## Autonomous repair contract

KRISHNA's repair path is:

1. collect evidence
2. form ranked hypotheses
3. create a disposable shadow copy
4. invoke only a pre-registered project action
5. run registered verification checks
6. reject the repair on any failed check
7. mark it promotable only when all checks pass
8. save incident, repair and verification evidence
9. review the result
10. keep live deployment as a separate policy-controlled operation

A successful edit alone is never completion.

## Core APIs

Read:
- `GET /health`
- `GET /api/dashboard`
- `GET /api/capabilities`
- `GET /api/projects`
- `GET /api/actions?project=...`
- `GET /api/resources`
- `GET /api/project-graph`
- `GET /api/incidents?project=...`
- `GET /api/recovery/ladder`

Work:
- `POST /api/projects/register`
- `POST /api/projects/index`
- `POST /api/investigate`
- `POST /api/repair/shadow`
- `POST /api/knowledge/ingest`
- `POST /api/security/scan-text`
- `POST /api/recovery/execute`

## Safety model

Natural-language input cannot directly execute arbitrary shell commands.
State-changing live recovery operations require pre-registered actions and the `KRISHNA_ALLOW_ACTIONS` policy flag.
Shadow repairs execute only registered repair workers against disposable project copies.
Security scanning is defensive and intended only for KRISHNA-owned or explicitly authorized projects.
Cloud fallback is blocked for `local_only` and `restricted` registered projects.
KRISHNA must not report work as completed merely because code changed; completion requires verification evidence.

Secrets stay outside Git in environment variables or local config.
