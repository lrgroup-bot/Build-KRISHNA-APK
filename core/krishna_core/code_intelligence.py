from __future__ import annotations

from .integrations import IntegrationRegistry


class CodeIntelligence:
    """Unified adapter over codebase-memory, CALM and ARISE."""

    def __init__(self, integrations: IntegrationRegistry):
        self.integrations = integrations

    def architecture(self, project_path: str) -> dict:
        # CBM command names vary by installation surface; CLI mode is optional.
        # Return availability plus instructions unless an explicit supported CLI call succeeds.
        status = self.integrations.available("codebase_memory")
        return {
            "available": status,
            "backend": "codebase-memory-mcp",
            "project_path": project_path,
            "capabilities": [
                "architecture", "call_graph", "impact_analysis", "routes",
                "cross_service_links", "cross_repo_graph", "semantic_search",
            ],
        }

    def calm_status(self, project_path: str) -> dict:
        return {
            "available": self.integrations.available("calm"),
            "backend": "CALM",
            "project_path": project_path,
            "capabilities": [
                "caller_context", "write_gate", "hash_verified_edit",
                "syntax_validation", "diff_impact", "fitness_report",
            ],
        }

    def arise_status(self, project_path: str) -> dict:
        return {
            "available": self.integrations.available("arise"),
            "backend": "ARISE",
            "project_path": project_path,
            "scope": "Python specialist",
            "capabilities": ["data_flow_slice", "fault_localization", "context_bundle"],
        }

    def status(self, project_path: str = "") -> dict:
        return {
            "codebase_memory": self.architecture(project_path),
            "calm": self.calm_status(project_path),
            "arise": self.arise_status(project_path),
        }
