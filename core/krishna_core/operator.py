from __future__ import annotations

from .integrations import IntegrationRegistry


class ComputerOperator:
    """CUA adapter. KRISHNA supplies policy; CUA supplies GUI-driving capability."""

    def __init__(self, integrations: IntegrationRegistry):
        self.integrations = integrations

    def status(self) -> dict:
        return {
            "available": self.integrations.available("cua"),
            "backend": "cua",
            "modes": ["desktop", "browser", "isolated_sandbox"],
            "policy": "registered tasks only; visual result must be verified",
        }

    def diagnostic(self) -> dict:
        if not self.integrations.available("cua"):
            return {"ok": False, "available": False, "message": "CUA driver not installed"}
        # --help is non-mutating and suitable for installation verification.
        return self.integrations.run("cua", ["--help"], timeout=15)
