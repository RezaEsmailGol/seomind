"use client";

import { useState } from "react";
import { SearchCheck, ShieldCheck } from "lucide-react";
import { api } from "@/lib/api";
import type { Lang } from "@/lib/i18n";

export default function UrlInspector({ lang, title, body, placeholder, button }: { lang: Lang; title: string; body: string; placeholder: string; button: string }) {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function inspect() {
    if (!url.trim()) return;
    setLoading(true); setError(null); setResult(null);
    try { setResult(await api.inspectUrl(url.trim(), lang === "fa" ? "fa-IR" : "en-US")); }
    catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setLoading(false); }
  }

  const inspection = result?.inspectionResult as Record<string, unknown> | undefined;
  const indexStatus = inspection?.indexStatusResult as Record<string, unknown> | undefined;

  return (
    <section className="glass rounded-3xl p-6 md:p-7">
      <div className="flex items-start gap-4">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border border-emerald-400/20 bg-emerald-400/10"><SearchCheck className="h-5 w-5 text-emerald-300" /></div>
        <div><h2 className="text-xl font-black">{title}</h2><p className="mt-1 max-w-2xl text-sm leading-6 text-slate-400">{body}</p></div>
      </div>
      <div className="mt-5 flex flex-col gap-3 sm:flex-row">
        <input value={url} onChange={(e) => setUrl(e.target.value)} onKeyDown={(e) => e.key === "Enter" && inspect()} placeholder={placeholder} className="min-w-0 flex-1 rounded-xl border border-white/10 bg-slate-950/50 px-4 py-3 text-sm text-white outline-none transition placeholder:text-slate-600 focus:border-sky-400/40" />
        <button onClick={inspect} disabled={loading || !url.trim()} className="inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-400 px-5 py-3 text-sm font-black text-slate-950 transition hover:bg-emerald-300 disabled:opacity-50"><ShieldCheck className="h-4 w-4" />{loading ? "…" : button}</button>
      </div>
      {error && <div className="mt-4 rounded-xl border border-rose-400/20 bg-rose-400/10 p-4 text-sm text-rose-200">{error}</div>}
      {indexStatus && (
        <div className="mt-5 grid gap-3 md:grid-cols-3">
          {["verdict", "coverageState", "indexingState", "pageFetchState", "robotsTxtState", "lastCrawlTime"].map((key) => indexStatus[key] ? (
            <div key={key} className="rounded-xl border border-white/[0.06] bg-slate-950/30 p-4"><div className="text-[10px] uppercase tracking-wider text-slate-600">{key}</div><div className="mt-2 break-words text-sm font-bold text-slate-200">{String(indexStatus[key])}</div></div>
          ) : null)}
        </div>
      )}
    </section>
  );
}
