package com.krishna.mobile;

import android.app.*;
import android.os.*;
import android.content.*;
import android.content.pm.PackageManager;
import android.webkit.*;
import android.media.*;
import android.provider.MediaStore;
import android.graphics.Bitmap;
import android.util.Base64;
import java.net.*;
import java.io.*;
import javax.net.ssl.*;
import org.json.*;
import java.security.*;

public class MainActivity extends Activity {
  static final String CORE="/api/core/chat";
  static final String SPEAKER_ENGINE="LOCAL_VOICE_PROFILE_V2";
  static final int REQ_PERMISSIONS=41;
  static final int REQ_VISION_CAMERA=73;
  WebView web;
  Bridge bridge;
  String pendingVisionMode="";
  String pendingVisionName="";

  @Override public void onCreate(Bundle b){
    super.onCreate(b);
    requestRuntimePermissions();
    web=new WebView(this);
    web.getSettings().setJavaScriptEnabled(true);
    web.getSettings().setDomStorageEnabled(true);
    web.getSettings().setAllowFileAccess(true);
    web.setWebChromeClient(new WebChromeClient(){
      @Override public void onPermissionRequest(PermissionRequest request){
        runOnUiThread(()->{
          if(Build.VERSION.SDK_INT<23 || checkSelfPermission(android.Manifest.permission.RECORD_AUDIO)==PackageManager.PERMISSION_GRANTED)
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

  void requestRuntimePermissions(){
    if(Build.VERSION.SDK_INT<23)return;
    java.util.ArrayList<String> p=new java.util.ArrayList<>();
    if(checkSelfPermission(android.Manifest.permission.RECORD_AUDIO)!=PackageManager.PERMISSION_GRANTED)
      p.add(android.Manifest.permission.RECORD_AUDIO);
    if(checkSelfPermission(android.Manifest.permission.CAMERA)!=PackageManager.PERMISSION_GRANTED)
      p.add(android.Manifest.permission.CAMERA);
    if(!p.isEmpty())requestPermissions(p.toArray(new String[0]),REQ_PERMISSIONS);
  }

  void openVisionCamera(String mode,String name){
    runOnUiThread(()->{
      if(Build.VERSION.SDK_INT>=23 && checkSelfPermission(android.Manifest.permission.CAMERA)!=PackageManager.PERMISSION_GRANTED){
        visionCallback("{\"error\":\"Camera permission is required for KRISHNA Vision.\"}");
        requestRuntimePermissions();
        return;
      }
      pendingVisionMode=mode;
      pendingVisionName=name==null?"":name.trim();
      Intent intent=new Intent(MediaStore.ACTION_IMAGE_CAPTURE);
      if(intent.resolveActivity(getPackageManager())==null){
        visionCallback("{\"error\":\"No camera application is available.\"}");
        return;
      }
      startActivityForResult(intent,REQ_VISION_CAMERA);
    });
  }

  @Override protected void onActivityResult(int requestCode,int resultCode,Intent data){
    super.onActivityResult(requestCode,resultCode,data);
    if(requestCode!=REQ_VISION_CAMERA)return;
    if(resultCode!=RESULT_OK || data==null || data.getExtras()==null){
      visionCallback("{\"error\":\"Face capture cancelled.\"}");
      return;
    }
    Object raw=data.getExtras().get("data");
    if(!(raw instanceof Bitmap)){
      visionCallback("{\"error\":\"Camera did not return a usable image.\"}");
      return;
    }
    Bitmap bitmap=(Bitmap)raw;
    ByteArrayOutputStream out=new ByteArrayOutputStream();
    bitmap.compress(Bitmap.CompressFormat.JPEG,92,out);
    String image64=Base64.encodeToString(out.toByteArray(),Base64.NO_WRAP);
    String mode=pendingVisionMode;
    String name=pendingVisionName;
    pendingVisionMode="";
    pendingVisionName="";
    new Thread(()->{
      try{
        JSONObject body=new JSONObject();
        body.put("image_base64",image64);
        body.put("device","krishna-mobile-primary");
        String path="/api/vision/recognize";
        if("enroll".equals(mode)){
          body.put("name",name);
          body.put("consent",true);
          path="/api/vision/enroll";
        }
        String result=bridge.call(path,body.toString());
        visionCallback(result);
      }catch(Exception e){
        visionCallback("{\"error\":"+JSONObject.quote(String.valueOf(e.getMessage()))+"}");
      }
    }).start();
  }

  void visionCallback(String json){
    if(web==null)return;
    runOnUiThread(()->web.evaluateJavascript(
      "window.krishnaVisionResult("+JSONObject.quote(json)+")",null
    ));
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
    @JavascriptInterface public String state(){ return call("/api/core/state",null); }
    @JavascriptInterface public String chat(String m){ return call(CORE,"{\"message\":"+JSONObject.quote(m)+",\"project\":\"general\"}"); }
    @JavascriptInterface public String visionStatus(){ return call("/api/vision/status",null); }
    @JavascriptInterface public void scanFace(){ openVisionCamera("scan",""); }
    @JavascriptInterface public void enrollFace(String name){ openVisionCamera("enroll",name); }
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
        return "{\"ok\":true}";
      }catch(Exception e){ return "{\"error\":"+JSONObject.quote(String.valueOf(e.getMessage()))+"}"; }
    }
    HttpsURLConnection conn(String path)throws Exception{
      HttpsURLConnection c=(HttpsURLConnection)new URL("https://192.168.0.106:8765"+path).openConnection();
      c.setConnectTimeout(4000); c.setReadTimeout(120000);
      c.setRequestProperty("Authorization","Device "+token());
      c.setRequestProperty("X-Krishna-Device","android-primary");
      c.setRequestProperty("Accept","application/json");
      return c;
    }
    byte[] callBytes(String path){
      try{
        HttpsURLConnection c=conn(path);
        InputStream in=c.getResponseCode()<400?c.getInputStream():c.getErrorStream();
        ByteArrayOutputStream o=new ByteArrayOutputStream(); byte[]b=new byte[8192];
        for(int n;(n=in.read(b))>0;)o.write(b,0,n);
        return c.getResponseCode()<400?o.toByteArray():null;
      }catch(Exception e){ return null; }
    }
    String call(String path,String body){
      try{
        HttpsURLConnection c=conn(path);
        if(body!=null){
          c.setRequestMethod("POST"); c.setDoOutput(true); c.setRequestProperty("Content-Type","application/json");
          c.getOutputStream().write(body.getBytes("UTF-8"));
        }
        InputStream in=c.getResponseCode()<400?c.getInputStream():c.getErrorStream();
        ByteArrayOutputStream o=new ByteArrayOutputStream(); byte[]b=new byte[4096];
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
