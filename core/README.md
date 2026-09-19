# KRISHNA Core

Local PC authority for KRISHNA Mobile.

KRISHNA is designed as a persistent autonomous software intelligence:

Observe -> Understand -> Investigate -> Research -> Plan -> Act -> Test -> Verify -> Learn.

## Components

- secure gateway/API
- persistent project + incident memory
- Project Graph for component/dependency relationships
- Evidence Engine with registered safe probes
- hypothesis-based Investigation Engine
- Knowledge Ingestor for text/webpage/document content
- planner/orchestrator
- worker registry
- local/cloud model router
- health watcher with state transitions
- verification gates
- policy-driven autonomous recovery ladder
- defensive static-security scanner
- rollback hooks
- audit log

## Safety model

Natural-language input cannot directly execute arbitrary shell commands.
State-changing recovery operations require pre-registered actions and the KRISHNA_ALLOW_ACTIONS policy flag.
Security scanning is defensive and intended only for KRISHNA-owned or explicitly authorized projects.
KRISHNA must not report work as completed merely because code changed; completion requires verification evidence.

Secrets stay outside Git in environment variables or local config.
