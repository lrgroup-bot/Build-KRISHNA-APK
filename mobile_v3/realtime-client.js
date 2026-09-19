/* KRISHNA Mobile resilient transport state machine.
   Android bridge may provide websocket later; this protocol also works over polling. */
class KrishnaRealtime {
  constructor(api){
    this.api=api; this.seq=Number(localStorage.getItem('krishna_seq')||0);
    this.attempt=0; this.maxAttempts=12; this.timer=null; this.connected=false;
  }
  backoff(){const cap=Math.min(500*Math.pow(2,this.attempt++),30000);return Math.floor(cap*(.5+Math.random()*.5))}
  start(){this.stop();this.sync()}
  stop(){if(this.timer)clearTimeout(this.timer);this.timer=null}
  sync(){
    try{
      const r=JSON.parse(this.api.resume(this.seq));
      if(r.error)throw new Error(r.error);
      this.connected=true;this.attempt=0;
      for(const e of (r.events||[])){this.seq=Math.max(this.seq,Number(e.seq||0));this.onEvent?.(e)}
      localStorage.setItem('krishna_seq',String(this.seq));
      this.timer=setTimeout(()=>this.sync(),3000);
    }catch(e){
      this.connected=false;
      if(this.attempt>=this.maxAttempts){this.onState?.('disconnected');return}
      this.onState?.('reconnecting');this.timer=setTimeout(()=>this.sync(),this.backoff());
    }
  }
}
