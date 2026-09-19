package com.krishna.mobile;

import android.app.*;
import android.os.*;
import android.content.*;
import android.content.pm.PackageManager;
import android.webkit.*;
import android.media.*;
import android.util.Base64;
import java.net.*;
import java.io.*;
import org.json.*;
import java.security.*;

public class MainActivity extends Activity {
  static final String CORE="/api/core/chat";
  static final String SPEAKER_ENGINE="LOCAL_VOICE_PROFILE_V2";
  WebView web;
  Bridge bridge;

  @Override public void onCreate(Bundle b){
    super.onCreate(b);
    if(Build.VERSION.SDK_INT>=23 && checkSelfPermission(android.Manifest.permission.RECORD_AUDIO)!=PackageManager.PERMISSION_GRANTED)
      requestPermissions(new String[]{android.Manifest.permission.RECORD_AUDIO},41);
    web=new WebView(this);
    web.getSettings().setJavaScriptEnabled(true);
    web.getSettings().setDomStorageEnabled(true);
    web.getSettings().setAllowFileAccess(true);
    web.setWebChromeClient(new WebChromeClient(){
      @Override public void onPermissionRequest(PermissionRequest request){
        runOnUiThread(()->{
          if(Build.VERSION.SDK_INT>=23 && checkSelfPermission(android.Manifest.permission.RECORD_AUDIO)==PackageManager.PERMISSION_GRANTED)
            request.grant(request.getResources());
          else request.deny();
        });
      }
    });
    bridge=new Bridge();
    web.addJavascriptInterface(bridge,"Krishna");
    setContentView(web);
    web.loadUrl("file:///android_asset/index.html");
  }

  void emitAsync(String kind,String detail){
    if(bridge==null)return;
    new Thread(()->bridge.event(kind,detail)).start();
  }

  @Override protected void onResume(){
    super.onResume();
    emitAsync("mobile_foreground","KRISHNA Mobile entered foreground");
  }

  @Override protected void onPause(){
    emitAsync("mobile_background","KRISHNA Mobile entered background");
    super.onPause();
  }

  public class Bridge {
    Bridge(){ ensureCredential(); }
    String token(){ return getSharedPreferences("k",0).getString("device_credential",""); }
    void ensureCredential(){
      if(token().isEmpty()){
        String id=java.util.UUID.randomUUID().toString()+"-"+java.util.UUID.randomUUID().toString();
        getSharedPreferences("k",0).edit().putString("device_credential",id).apply();
      }
    }
    @JavascriptInterface public String status(){ return call("/api/status",null); }
    @JavascriptInterface public String connection(){ return call("/api/mobile/connection",null); }
    @JavascriptInterface public String event(String kind,String detail){
      return call("/api/core/event","{\"source\":\"mobile\",\"kind\":"+JSONObject.quote(kind)+",\"detail\":"+JSONObject.quote(detail)+",\"project\":\"system\"}");
    }
    @JavascriptInterface public String state(){ return call("/api/core/state",null); }
    @JavascriptInterface public String projects(){ return call("/api/projects",null); }
    @JavascriptInterface public String chats(String project){
      return call("/api/chats?project="+urlEncode(project),null);
    }
    @JavascriptInterface public String newChat(String project,String title){
      return call("/api/chats/create","{\"project\":"+JSONObject.quote(project)+",\"title\":"+JSONObject.quote(title)+"}");
    }
    @JavascriptInterface public void setWorkspace(String project,String chatId){
      getSharedPreferences("k",0).edit()
        .putString("active_project",project==null?"general":project)
        .putString("active_chat",chatId==null?"":chatId).apply();
    }
    @JavascriptInterface public String workspace(){
      try{
        JSONObject j=new JSONObject();
        j.put("project",getSharedPreferences("k",0).getString("active_project","general"));
        j.put("chat_id",getSharedPreferences("k",0).getString("active_chat",""));
        return j.toString();
      }catch(Exception e){ return "{\"project\":\"general\",\"chat_id\":\"\"}"; }
    }
    @JavascriptInterface public String chat(String m){
      String project=getSharedPreferences("k",0).getString("active_project","general");
      String chatId=getSharedPreferences("k",0).getString("active_chat","");
      String body="{\"message\":"+JSONObject.quote(m)+",\"project\":"+JSONObject.quote(project)+
        ",\"chat_id\":"+(chatId.isEmpty()?"null":JSONObject.quote(chatId))+",\"source\":\"mobile\"}";
      return call(CORE,body);
    }
    @JavascriptInterface public String control(String action,String payloadJson){
      try{
        JSONObject body=new JSONObject();
        body.put("action",action);
        body.put("project",getSharedPreferences("k",0).getString("active_project","general"));
        body.put("chat_id",getSharedPreferences("k",0).getString("active_chat",""));
        if(payloadJson!=null && !payloadJson.trim().isEmpty()) body.put("payload",new JSONObject(payloadJson));
        else body.put("payload",new JSONObject());
        return call("/api/mobile/control",body.toString());
      }catch(Exception e){ return "{\"error\":"+JSONObject.quote(String.valueOf(e.getMessage()))+"}"; }
    }
    String urlEncode(String value){
      try{return URLEncoder.encode(value==null?"":value,"UTF-8");}catch(Exception e){return "";}
    }
    @JavascriptInterface public String avatarBase64(){
      byte[] b=callBytes("/api/avatar");
      return b==null?"":Base64.encodeToString(b,Base64.NO_WRAP);
    }
    @JavascriptInterface public void log(String e){ call("/api/mobile-log","{\"event\":"+JSONObject.quote(e)+"}"); }
    @JavascriptInterface public boolean voiceEnrolled(){ return getSharedPreferences("k",0).getBoolean("voice_enrolled",false); }
    @JavascriptInterface public String enrollVoice(){
      try{
        String fp=VoicePrint.capture(MainActivity.this,3200);
        getSharedPreferences("k",0).edit().putString("voiceprint",fp).putString("speaker_engine",SPEAKER_ENGINE).putBoolean("voice_enrolled",true).apply();
        event("voice_enrolled","Local owner voice profile enrolled");
        return "{\"ok\":true}";
      }catch(Exception e){ return "{\"error\":"+JSONObject.quote(String.valueOf(e.getMessage()))+"}"; }
    }
    HttpURLConnection conn(String path)throws Exception{
      String base=getSharedPreferences("k",0).getString("core_url","http://192.168.0.106:8766");
      HttpURLConnection c=(HttpURLConnection)new URL(base+path).openConnection();
      c.setConnectTimeout(4000); c.setReadTimeout(120000);
      c.setRequestProperty("Authorization","Device "+token());
      c.setRequestProperty("X-Krishna-Device","android-primary");
      c.setRequestProperty("Accept","application/json");
      return c;
    }
    byte[] callBytes(String path){
      try{
        HttpURLConnection c=conn(path);
        InputStream in=c.getResponseCode()<400?c.getInputStream():c.getErrorStream();
        ByteArrayOutputStream o=new ByteArrayOutputStream(); byte[]b=new byte[8192];
        for(int n;(n=in.read(b))>0;)o.write(b,0,n);
        return c.getResponseCode()<400?o.toByteArray():null;
      }catch(Exception e){ return null; }
    }
    String call(String path,String body){
      try{
        HttpURLConnection c=conn(path);
        if(body!=null){
          c.setRequestMethod("POST"); c.setDoOutput(true); c.setRequestProperty("Content-Type","application/json");
          c.getOutputStream().write(body.getBytes("UTF-8"));
        }
        InputStream in=c.getResponseCode()<400?c.getInputStream():c.getErrorStream();
        ByteArrayOutputStream o=new ByteArrayOutputStream(); byte[]b=new byte[2048];
        for(int n;(n=in.read(b))>0;)o.write(b,0,n);
        return o.toString("UTF-8");
      }catch(Exception e){
        return "{\"error\":"+JSONObject.quote(e.getClass().getSimpleName()+": "+String.valueOf(e.getMessage()))+"}";
      }
    }
  }
}

class VoicePrint{
  static String capture(Context c,int ms)throws Exception{
    int rate=16000,bs=AudioRecord.getMinBufferSize(rate,AudioFormat.CHANNEL_IN_MONO,AudioFormat.ENCODING_PCM_16BIT);
    AudioRecord a=new AudioRecord(MediaRecorder.AudioSource.VOICE_RECOGNITION,rate,AudioFormat.CHANNEL_IN_MONO,AudioFormat.ENCODING_PCM_16BIT,Math.max(bs,4096));
    short[]b=new short[1024]; MessageDigest d=MessageDigest.getInstance("SHA-256"); long end=System.currentTimeMillis()+ms;
    a.startRecording();
    while(System.currentTimeMillis()<end){
      int n=a.read(b,0,b.length);
      if(n>0){
        long energy=0,z=0;
        for(int i=1;i<n;i++){energy+=Math.abs(b[i]);if((b[i]>=0)!=(b[i-1]>=0))z++;}
        d.update(((energy/Math.max(1,n)/128)+":"+(z/4)+";").getBytes("UTF-8"));
      }
    }
    a.stop(); a.release(); StringBuilder x=new StringBuilder();
    for(byte q:d.digest())x.append(String.format("%02x",q)); return x.toString();
  }
}
