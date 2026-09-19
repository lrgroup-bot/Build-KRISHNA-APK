from __future__ import annotations

import hashlib
import re
import time
from typing import List


class KnowledgeIngestor:
    """Turns text/webpage/document text into deduplicated chunks for persistent memory."""

    def __init__(self, memory_store, max_chunk_chars: int = 3500):
        self.memory = memory_store
        self.max_chunk_chars = max(500, max_chunk_chars)

    @staticmethod
    def _clean(text: str) -> str:
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def chunk(self, text: str) -> List[str]:
        text = self._clean(text)
        if not text:
            return []
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks: List[str] = []
        current = ""
        for para in paragraphs:
            candidate = para if not current else current + "\n\n" + para
            if len(candidate) <= self.max_chunk_chars:
                current = candidate
                continue
            if current:
                chunks.append(current)
            while len(para) > self.max_chunk_chars:
                chunks.append(para[: self.max_chunk_chars])
                para = para[self.max_chunk_chars :]
            current = para
        if current:
            chunks.append(current)
        return chunks

    def ingest(self, project: str, source: str, text: str, metadata: dict | None = None) -> dict:
        chunks = self.chunk(text)
        written = 0
        for index, chunk in enumerate(chunks):
            digest = hashlib.sha256(chunk.encode("utf-8")).hexdigest()
            if self.memory.has_content_hash(project, digest):
                continue
            md = dict(metadata or {})
            md.update({
                "source": source,
                "chunk_index": index,
                "sha256": digest,
                "ingested_at": time.time(),
            })
            self.memory.remember(project, "knowledge", chunk, md)
            written += 1
        return {"chunks": len(chunks), "written": written, "duplicates": len(chunks) - written}
