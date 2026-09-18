import uuid, time
from .memory import MemoryStore
from .router import ModelRouter
from .config import settings

class Orchestrator:
    def __init__(self):
        self.memory=MemoryStore(); self.router=ModelRouter()
    def handle(self, message, project="general"):
        task_id=str(uuid.uuid4())
        self.memory.audit(task_id,"received",message)
        context=self.memory.recall(project,10)
        prompt=f"""You are KRISHNA Core. Be concise and truthful. Never claim an action completed unless verified.
Project: {project}
Recent memory: {context}
User: {message}
If this requires an action, describe the action plan. Do not execute arbitrary shell commands from natural language."""
        result=self.router.auto(prompt)
        self.memory.remember(project,"conversation",message,{"task_id":task_id})
        self.memory.audit(task_id,"answered",result["provider"])
        return {"task_id":task_id,**result}
