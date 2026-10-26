"""Read-only integrity gate for a packaged KRISHNA-CORE source snapshot.

This does not prove that a GitHub revision is deployed, signed or running.
"""
from __future__ import annotations
from pathlib import Path
from hashlib import sha256
import re

COMMIT=re.compile(r"^[0-9a-f]{40}$")
SHA256=re.compile(r"^[0-9a-f]{64}$")


def verify_source_manifest(root: str | Path, manifest: dict) -> dict:
    root=Path(root).resolve()
    problems=[]
    if not isinstance(manifest,dict):
        return {"ok":False,"errors":["manifest_required"],"runtime_verified":False}
    if manifest.get("canonical_repository")!="lrgroup-bot/KRISHNA-CORE":
        problems.append("wrong_canonical_repository")
    if not COMMIT.fullmatch(str(manifest.get("canonical_commit",""))):
        problems.append("canonical_commit_sha_required")
    paths=manifest.get("file_hashes")
    if not isinstance(paths,dict) or not paths:
        paths={}
        problems.append("nonempty_hash_manifest_required")
    checked=0
    for name,expected in paths.items():
        if not isinstance(name,str) or not SHA256.fullmatch(str(expected)):
            problems.append("invalid_path_or_sha256")
            continue
        target=(root/name).resolve()
        if target==root or root not in target.parents:
            problems.append("path_outside_source_root")
            continue
        if not target.is_file():
            problems.append("source_file_missing")
            continue
        if sha256(target.read_bytes()).hexdigest()!=expected:
            problems.append("source_hash_mismatch")
            continue
        checked+=1
    return {"ok":not problems, "errors":problems,"checked":checked,
            "source_integrity_only":True,"runtime_verified":False,
            "signing_verified":False,
            "note":"Canonical repo commit, build signature and Android on-device behavior require separate verification."}
