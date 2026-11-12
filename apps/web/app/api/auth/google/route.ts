import { NextResponse } from "next/server";
import { randomBytes, createHash } from "node:crypto";
import { base, callback, scope } from "@/lib/gsc-auth";
export const runtime = "nodejs";
export async function GET() { if (!process.env.GOOGLE_CLIENT_ID || !process.env.GOOGLE_CLIENT_SECRET || !process.env.SESSION_SECRET) return NextResponse.redirect(new URL("/?error=configuration",base));
 const state=randomBytes(24).toString("base64url"), verifier=randomBytes(32).toString("base64url");
 const challenge=createHash("sha256").update(verifier).digest("base64url");
 const u=new URL("https://accounts.google.com/o/oauth2/v2/auth"); for(const [k,v] of Object.entries({client_id:process.env.GOOGLE_CLIENT_ID || "",redirect_uri:callback,response_type:"code",scope,access_type:"offline",prompt:"consent",state,code_challenge:challenge,code_challenge_method:"S256"})) u.searchParams.set(k,v);
 const r=NextResponse.redirect(u); for(const [name,value] of [["gsc_state",state],["gsc_verifier",verifier]]) r.cookies.set(name,value,{httpOnly:true,secure:true,sameSite:"lax",path:"/",maxAge:600}); return r;
}
