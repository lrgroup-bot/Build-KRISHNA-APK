from __future__ import annotations

import base64
import json
import mimetypes
import time
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class VisionMatch:
    state: str
    subject: str | None
    similarity: float
    faces_detected: int
    source: str = "local_enrolled_gallery"


def classify_compreface_response(
    payload: dict[str, Any],
    known_threshold: float = 0.80,
    possible_threshold: float = 0.65,
) -> VisionMatch:
    results = payload.get("result") or []
    faces_detected = len(results)
    best_subject = None
    best_similarity = 0.0

    for face in results:
        for candidate in face.get("subjects") or []:
            try:
                similarity = float(candidate.get("similarity", 0.0))
            except (TypeError, ValueError):
                similarity = 0.0
            subject = str(candidate.get("subject", "")).strip() or None
            if subject and similarity > best_similarity:
                best_subject = subject
                best_similarity = similarity

    if best_subject and best_similarity >= known_threshold:
        state = "KNOWN"
    elif best_subject and best_similarity >= possible_threshold:
        state = "POSSIBLE_MATCH"
    else:
        state = "UNKNOWN"
        best_subject = None

    return VisionMatch(
        state=state,
        subject=best_subject,
        similarity=round(best_similarity, 4),
        faces_detected=faces_detected,
    )


class CompreFaceClient:
    """Minimal client for a KRISHNA-controlled local CompreFace recognition service."""

    def __init__(self, base_url: str, api_key: str, timeout: int = 25):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.api_key)

    def _multipart(self, path: str, image: bytes, filename: str = "face.jpg") -> dict:
        boundary = "----krishna-" + uuid.uuid4().hex
        body = bytearray()
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode()
        )
        body.extend(b"Content-Type: image/jpeg\r\n\r\n")
        body.extend(image)
        body.extend(f"\r\n--{boundary}--\r\n".encode())

        req = urllib.request.Request(
            self.base_url + path,
            data=bytes(body),
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "x-api-key": self.api_key,
                "Accept": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def enroll(self, subject: str, image: bytes, det_threshold: float = 0.80) -> dict:
        subject_q = urllib.parse.quote(subject, safe="")
        path = (
            "/api/v1/recognition/faces"
            f"?subject={subject_q}&det_prob_threshold={det_threshold:.2f}"
        )
        return self._multipart(path, image)

    def recognize(self, image: bytes, det_threshold: float = 0.80) -> dict:
        path = (
            "/api/v1/recognition/recognize"
            f"?limit=1&prediction_count=3&det_prob_threshold={det_threshold:.2f}"
        )
        return self._multipart(path, image)


class VisionIdentityService:
    MAX_IMAGE_BYTES = 5 * 1024 * 1024

    def __init__(
        self,
        memory,
        base_url: str,
        api_key: str,
        known_threshold: float = 0.80,
        possible_threshold: float = 0.65,
    ):
        self.memory = memory
        self.client = CompreFaceClient(base_url, api_key)
        self.known_threshold = known_threshold
        self.possible_threshold = possible_threshold

    def status(self) -> dict:
        return {
            "configured": self.client.configured,
            "backend": "compreface-local",
            "identity_scope": "explicitly_enrolled_people_only",
            "states": ["KNOWN", "POSSIBLE_MATCH", "UNKNOWN"],
            "known_threshold": self.known_threshold,
            "possible_threshold": self.possible_threshold,
            "public_face_search": False,
        }

    def _decode_image(self, image_base64: str) -> bytes:
        if not image_base64:
            raise ValueError("image_base64 is required")
        try:
            image = base64.b64decode(image_base64, validate=True)
        except Exception as exc:
            raise ValueError("invalid base64 image") from exc
        if not image:
            raise ValueError("empty image")
        if len(image) > self.MAX_IMAGE_BYTES:
            raise ValueError("image exceeds 5 MB limit")
        return image

    @staticmethod
    def _subject(name: str) -> str:
        cleaned = " ".join(str(name).strip().split())
        if not cleaned:
            raise ValueError("name is required")
        if len(cleaned) > 80:
            raise ValueError("name is too long")
        return cleaned

    def enroll(self, name: str, image_base64: str, consent: bool, device: str = "unknown") -> dict:
        if not consent:
            raise ValueError("explicit enrollment consent is required")
        if not self.client.configured:
            raise RuntimeError("local face recognition backend is not configured")
        subject = self._subject(name)
        image = self._decode_image(image_base64)
        backend = self.client.enroll(subject, image)
        event = {
            "subject": subject,
            "device": device,
            "consent": True,
            "backend": "compreface-local",
            "enrolled_at": time.time(),
        }
        self.memory.remember("vision", "identity_enrollment", subject, event)
        self.memory.audit("vision_enroll", "complete", subject)
        return {
            "ok": True,
            "state": "ENROLLED",
            "subject": subject,
            "local_only": True,
            "backend_result": {"image_id": backend.get("image_id")},
        }

    def recognize(self, image_base64: str, device: str = "unknown") -> dict:
        if not self.client.configured:
            raise RuntimeError("local face recognition backend is not configured")
        image = self._decode_image(image_base64)
        payload = self.client.recognize(image)
        match = classify_compreface_response(
            payload,
            known_threshold=self.known_threshold,
            possible_threshold=self.possible_threshold,
        )
        result = {
            "state": match.state,
            "subject": match.subject,
            "similarity": match.similarity,
            "faces_detected": match.faces_detected,
            "source": match.source,
            "local_only": True,
            "public_face_search": False,
        }
        self.memory.remember(
            "vision",
            "recognition_event",
            match.state,
            {
                "device": device,
                "subject": match.subject,
                "similarity": match.similarity,
                "faces_detected": match.faces_detected,
            },
        )
        self.memory.audit("vision_recognize", "complete", json.dumps(result))
        return result
