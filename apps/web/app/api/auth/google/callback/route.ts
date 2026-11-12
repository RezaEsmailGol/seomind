import { NextRequest, NextResponse } from "next/server";
import { base,callback,seal,Tokens } from "@/lib/gsc-auth";
export const runtime="nodejs";
export async function GET(req:NextRequest) { const url=new URL(req.url),state=url.searchParams.get("state"),code=url.searchParams.get("code"); const saved=req.cookies.get("gsc_state")?.value,verifier=req.cookies.get("gsc_verifier")?.value;
 const failure=(reason:string)=>{const r=NextResponse.redirect(new URL("/?error="+encodeURIComponent(reason),base));r.cookies.delete("gsc_state");r.cookies.delete("gsc_verifier");return r;};
 if(url.searchParams.get("error")) return failure("google_denied");
 if(!state||!saved||state!==saved||!verifier||!code) return failure("invalid_state");
 try {const result=await fetch("https://oauth2.googleapis.com/token",{method:"POST",headers:{"Content-Type":"application/x-www-form-urlencoded"},body:new URLSearchParams({code,client_id:process.env.GOOGLE_CLIENT_ID||"",client_secret:process.env.GOOGLE_CLIENT_SECRET||"",redirect_uri:callback,grant_type:"authorization_code",code_verifier:verifier}),cache:"no-store"});if(!result.ok)return failure("token_exchange");const data=await result.json();const t:Tokens={access_token:data.access_token,refresh_token:data.refresh_token,expires_at:Date.now()+data.expires_in*1000};const r=NextResponse.redirect(new URL("/",base));r.cookies.set("seomind_session",seal(t),{httpOnly:true,secure:true,sameSite:"lax",path:"/",maxAge:60*60*24*30});r.cookies.delete("gsc_state");r.cookies.delete("gsc_verifier");return r;}catch{return failure("oauth_failed");}
}
