from __future__ import annotations
class ProjectBrain:
    def __init__(self,memory):self.memory=memory
    def learn_verified(self,project,goal,result):
        self.memory.remember(project,"verified_learning",goal,{"result":result})
        self.memory.audit("project_brain","learned",project)
    def context(self,project,limit=20):
        return {"project":project,"memory":self.memory.recall(project,limit=limit),"incidents":self.memory.incidents(project,limit=10)}
