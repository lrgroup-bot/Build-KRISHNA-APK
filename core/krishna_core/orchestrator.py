import uuid
from .memory import MemoryStore
from .router import ModelRouter
from .config import settings
from .project_graph import ProjectGraph
from .investigator import EvidenceEngine, InvestigationEngine, Evidence, Hypothesis
from .verification import VerificationEngine
from .recovery import RecoveryEngine
from .knowledge import KnowledgeIngestor
from .security import DefensiveSecurityScanner
from .identity import VisionIdentityService

class Orchestrator:
    def __init__(self):
        self.memory = MemoryStore()
        self.router = ModelRouter()
        self.graph = ProjectGraph()
        self.evidence = EvidenceEngine()
        self.investigator = InvestigationEngine(self.evidence)
        self.verifier = VerificationEngine()
        self.recovery = RecoveryEngine(allow_mutating_actions=settings.allow_actions)
        self.knowledge = KnowledgeIngestor(self.memory)
        self.security = DefensiveSecurityScanner()
        self.vision = VisionIdentityService(
            self.memory,
            settings.compreface_url,
            settings.compreface_api_key,
            known_threshold=settings.face_known_threshold,
            possible_threshold=settings.face_possible_threshold,
        )
        self._register_builtin_probes()

    def _register_builtin_probes(self):
        def memory_probe(context):
            project = context.get("project", "general")
            items = self.memory.recall(project, limit=8)
            for item in items:
                yield Evidence(
                    source="memory",
                    kind=item["kind"],
                    detail=item["content"][:1200],
                    confidence=0.75,
                )
        self.evidence.register_probe("memory", memory_probe)

        def graph_probe(context):
            seeds = context.get("components") or []
            if not seeds:
                return []
            subgraph = self.graph.relevant(seeds, depth=2)
            return [
                Evidence(
                    source="project_graph",
                    kind="dependency_context",
                    detail=str(subgraph),
                    confidence=0.90,
                )
            ]
        self.evidence.register_probe("project_graph", graph_probe)

    def _ai_hypotheses(self, symptom, evidence, context):
        evidence_text = "\n".join(
            f"- [{e.source}/{e.kind}] {e.detail[:1800]}" for e in evidence
        ) or "- no evidence collected"
        prompt = f"""You are KRISHNA's diagnostic reasoner.
Produce at most 5 concise root-cause hypotheses for an authorized software project.
Do not propose exploitation. Do not claim a cause is proven.
Return one hypothesis per line as: confidence|statement
Confidence is 0.00-1.00.

Project: {context.get('project', 'general')}
Symptom: {symptom}
Evidence:
{evidence_text}
"""
        try:
            result = self.router.auto(prompt)["text"]
            parsed = []
            sources = sorted({e.source for e in evidence})
            for raw in result.splitlines():
                if "|" not in raw:
                    continue
                left, statement = raw.split("|", 1)
                try:
                    confidence = min(1.0, max(0.0, float(left.strip())))
                except ValueError:
                    continue
                statement = statement.strip(" -\t")
                if statement:
                    parsed.append(Hypothesis(statement, confidence, supporting_sources=sources))
            if parsed:
                return parsed[:5]
        except Exception:
            pass
        return InvestigationEngine._baseline_hypotheses(symptom, evidence)

    def investigate(self, symptom, project="general", components=None):
        context = {"project": project, "components": components or []}
        report = self.investigator.investigate(
            symptom=symptom,
            context=context,
            hypothesis_builder=self._ai_hypotheses,
        )
        self.memory.save_incident(
            report["investigation_id"], project, symptom, status=report["status"]
        )
        self.memory.remember(
            project, "investigation", symptom,
            {"investigation_id": report["investigation_id"], "hypotheses": report["hypotheses"]}
        )
        self.memory.audit(report["investigation_id"], "investigated", project)
        return report

    def ingest_knowledge(self, project, source, text, metadata=None):
        result = self.knowledge.ingest(project, source, text, metadata)
        self.memory.audit("knowledge_ingest", "complete", f"{project}:{source}:{result}")
        return result

    def handle(self, message, project="general"):
        task_id = str(uuid.uuid4())
        self.memory.audit(task_id, "received", message)
        context = self.memory.recall(project, 12)
        incidents = self.memory.incidents(project, 5)
        prompt = f"""You are KRISHNA Core, a persistent autonomous software intelligence.
Operating loop: Observe -> Understand -> Investigate -> Research -> Plan -> Act -> Test -> Verify -> Learn.
Be concise and truthful. Never claim an action completed unless verification evidence exists.
Never execute arbitrary shell commands from natural language. Mutating actions must use registered workers/policies.

Project: {project}
Recent memory: {context}
Recent incidents: {incidents}
User: {message}

If the request describes a failure, recommend investigation and evidence collection before modification.
If it requires an action, describe the bounded action and verification criteria.
"""
        result = self.router.auto(prompt)
        self.memory.remember(project, "conversation", message, {"task_id": task_id})
        self.memory.audit(task_id, "answered", result["provider"])
        return {"task_id": task_id, **result}
