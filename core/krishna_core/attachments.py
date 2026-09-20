from __future__ import annotations
import base64, hashlib, json, re, time, uuid
from pathlib import Path

_SAFE=re.compile(r"[^A-Za-z0-9._-]+")

class AttachmentStore:
    def __init__(self,state_dir):
        self.root=Path(state_dir).resolve()/"attachments"; self.root.mkdir(parents=True,exist_ok=True)

    def save(self,chat_id,name,data_b64,content_type="application/octet-stream"):
        name=_SAFE.sub("_",str(name or "file"))[:160]
        raw=base64.b64decode(str(data_b64 or ""),validate=True)
        if not raw: raise ValueError("attachment is empty")
        if len(raw)>25*1024*1024: raise ValueError("attachment exceeds 25 MB")
        aid=str(uuid.uuid4()); folder=self.root/str(chat_id)
        folder.mkdir(parents=True,exist_ok=True)
        path=folder/(aid+"-"+name); path.write_bytes(raw)
        meta={"attachment_id":aid,"chat_id":str(chat_id),"name":name,"content_type":str(content_type)[:120],"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest(),"created_at":time.time(),"path":str(path)}
        path.with_suffix(path.suffix+".json").write_text(json.dumps(meta,indent=2),encoding="utf-8")
        return {k:v for k,v in meta.items() if k!="path"}

    def list(self,chat_id):
        folder=self.root/str(chat_id)
        if not folder.is_dir():return []
        out=[]
        for p in folder.glob("*.json"):
            try:
                row=json.loads(p.read_text("utf-8")); row.pop("path",None); out.append(row)
            except Exception:pass
        return sorted(out,key=lambda x:x.get("created_at",0))
