import { createCipheriv, createDecipheriv, randomBytes, createHash } from "node:crypto";
import { cookies } from "next/headers";
export const scope = "https://www.googleapis.com/auth/webmasters.readonly";
export const base = process.env.NEXT_PUBLIC_APP_URL || "https://seomind-web.vercel.app";
export const callback = base.replace(/\/$/, "") + "/api/auth/google/callback";
function key() { const value = process.env.SESSION_SECRET; if (!value || value.length < 32) throw new Error("SESSION_SECRET must be at least 32 characters"); return createHash("sha256").update(value).digest(); }
export function seal(value: unknown) { const iv = randomBytes(12); const cipher = createCipheriv("aes-256-gcm", key(), iv); const data = Buffer.concat([cipher.update(JSON.stringify(value)), cipher.final()]); return Buffer.concat([iv, cipher.getAuthTag(), data]).toString("base64url"); }
export function unseal<T>(raw: string): T { const buf = Buffer.from(raw, "base64url"); const decipher = createDecipheriv("aes-256-gcm", key(), buf.subarray(0,12)); decipher.setAuthTag(buf.subarray(12,28)); return JSON.parse(Buffer.concat([decipher.update(buf.subarray(28)), decipher.final()]).toString()) as T; }
export type Tokens = { access_token: string; refresh_token?: string; expires_at: number };
export async function getAccessToken() { const jar = await cookies(); const raw = jar.get("seomind_session")?.value; if (!raw) return null; let t: Tokens; try { t = unseal<Tokens>(raw); } catch { return null; }
 if (Date.now() < t.expires_at - 60000) return t.access_token;
 if (!t.refresh_token) return null;
 const res = await fetch("https://oauth2.googleapis.com/token", { method:"POST", headers:{"Content-Type":"application/x-www-form-urlencoded"}, body:new URLSearchParams({client_id:process.env.GOOGLE_CLIENT_ID || "",client_secret:process.env.GOOGLE_CLIENT_SECRET || "",refresh_token:t.refresh_token,grant_type:"refresh_token"}), cache:"no-store" });
 if (!res.ok) return null; const next = await res.json(); t = {...t,access_token:next.access_token,expires_at:Date.now()+next.expires_in*1000}; jar.set("seomind_session",seal(t),{httpOnly:true,secure:true,sameSite:"lax",path:"/",maxAge:60*60*24*30}); return t.access_token;
}
export async function googleGet(path: string) { const token = await getAccessToken(); if (!token) return Response.json({error:"not_authenticated"},{status:401}); const response = await fetch("https://www.googleapis.com/webmasters/v3/"+path,{headers:{Authorization:"Bearer "+token},cache:"no-store"}); return new Response(await response.text(),{status:response.status,headers:{"Content-Type":"application/json","Cache-Control":"no-store"}}); }
