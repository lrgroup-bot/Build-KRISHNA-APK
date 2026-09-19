from __future__ import annotations

import ast
import hashlib
from pathlib import Path


class RepositoryIndexer:
    """Small local code-intelligence indexer inspired by graph/code-memory systems."""

    DEFAULT_EXTENSIONS = {".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".kt", ".json", ".yml", ".yaml", ".html", ".css"}

    def __init__(self, max_file_bytes: int = 1_000_000):
        self.max_file_bytes = max_file_bytes

    def index(self, root: str | Path) -> dict:
        root = Path(root).resolve()
        files, symbols, imports = [], [], []
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in self.DEFAULT_EXTENSIONS:
                continue
            try:
                if path.stat().st_size > self.max_file_bytes:
                    continue
                raw = path.read_bytes()
                text = raw.decode("utf-8", errors="replace")
            except OSError:
                continue
            rel = str(path.relative_to(root)).replace("\\", "/")
            files.append({
                "path": rel,
                "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            })
            if path.suffix.lower() == ".py":
                try:
                    tree = ast.parse(text)
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                            symbols.append({"file": rel, "name": node.name, "kind": type(node).__name__, "line": node.lineno})
                        elif isinstance(node, ast.Import):
                            imports.extend({"file": rel, "module": n.name} for n in node.names)
                        elif isinstance(node, ast.ImportFrom):
                            imports.append({"file": rel, "module": node.module or ""})
                except SyntaxError:
                    pass
        return {"root": str(root), "file_count": len(files), "files": files, "symbols": symbols, "imports": imports}
