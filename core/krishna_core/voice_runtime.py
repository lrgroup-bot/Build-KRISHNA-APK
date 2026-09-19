from __future__ import annotations
class VoiceRuntime:
 """Provider-neutral local voice boundary. Engines are injected; no cloud dependency is assumed."""
 def __init__(self,stt=None,tts=None):self.stt=stt;self.tts=tts
 def status(self):return {"stt":bool(self.stt),"tts":bool(self.tts),"mode":"local_provider"}
 def transcribe(self,audio_path):
  if not self.stt:raise RuntimeError("local STT provider not configured")
  return self.stt(audio_path)
 def speak(self,text,output_path=None):
  if not self.tts:raise RuntimeError("local TTS provider not configured")
  return self.tts(text,output_path)
