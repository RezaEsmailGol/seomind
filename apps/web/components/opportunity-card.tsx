"use client";

import { useState } from "react";
import { Bot, ChevronDown, ExternalLink, Sparkles } from "lucide-react";
import { api, type Opportunity } from "@/lib/api";
import type { Lang } from "@/lib/i18n";

export default function OpportunityCard({ item, lang, labels, reason, aiAvailable }: { item: Opportunity; lang: Lang; labels: string; reason: string; aiAvailable: boolean }) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [explanation, setExplanation] = useState<{ summary: string; why_it_matters: string; actions: string[]; model: string } | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function explain() {
    if (!aiAvailable) return;
    setLoading(true);
    setError(null);
    try {
      setExplanation(await api.explain(item, lang));
      setOpen(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <article className="glass rounded-2xl p-5 transition hover:border-sky-400/20">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <span className="rounded-full border border-sky-400/20 bg-sky-400/10 px-2.5 py-1 text-xs font-bold text-sky-200">{labels}</span>
            <span className="rounded-full border border-violet-400/20 bg-violet-400/10 px-2.5 py-1 text-xs font-bold text-violet-200">{item.score}/100</span>
          </div>
          <h3 className="truncate text-base font-bold text-white" title={item.query}>{item.query || "—"}</h3>
          <a href={item.page} target="_blank" rel="noreferrer" className="mt-1 flex max-w-xl items-center gap-1.5 truncate text-xs text-slate-500 hover:text-sky-300">
            <span className="truncate">{item.page}</span><ExternalLink className="h-3 w-3 shrink-0" />
          </a>
        </div>
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.04] text-lg font-black text-sky-200">{item.score}</div>
      </div>

      <p className="mt-4 text-sm leading-6 text-slate-400">{reason}</p>

      <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
        {Object.entries(item.metrics).slice(0, 4).map(([key, value]) => (
          <div key={key} className="rounded-xl border border-white/[0.06] bg-slate-950/30 px-3 py-2">
            <div className="truncate text-[10px] uppercase tracking-wider text-slate-600">{key.replaceAll("_", " ")}</div>
            <div className="mt-1 text-sm font-bold text-slate-200">{key === "ctr" ? `${(value * 100).toFixed(2)}%` : Number(value).toLocaleString()}</div>
          </div>
        ))}
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <button disabled={!aiAvailable || loading} onClick={explain} className="inline-flex items-center gap-2 rounded-xl border border-violet-400/20 bg-violet-400/10 px-3.5 py-2 text-xs font-bold text-violet-200 transition hover:bg-violet-400/15 disabled:cursor-not-allowed disabled:opacity-40">
          {loading ? <Sparkles className="h-4 w-4 animate-pulse" /> : <Bot className="h-4 w-4" />}
          {lang === "fa" ? (loading ? "در حال تحلیل…" : "توضیح با AI محلی") : (loading ? "Explaining…" : "Explain with local AI")}
        </button>
        {explanation && (
          <button onClick={() => setOpen(!open)} className="inline-flex items-center gap-1 text-xs font-semibold text-slate-400 hover:text-white">
            {lang === "fa" ? "نمایش توضیح" : "Show explanation"}<ChevronDown className={`h-4 w-4 transition ${open ? "rotate-180" : ""}`} />
          </button>
        )}
      </div>

      {error && <div className="mt-3 rounded-xl border border-rose-400/20 bg-rose-400/10 p-3 text-xs text-rose-200">{error}</div>}
      {explanation && open && (
        <div className="mt-4 rounded-2xl border border-violet-400/15 bg-violet-400/[0.06] p-4 text-sm leading-7 text-slate-300">
          <div className="font-bold text-white">{explanation.summary}</div>
          {explanation.why_it_matters && <p className="mt-2 text-slate-400">{explanation.why_it_matters}</p>}
          <ol className="mt-3 space-y-2">
            {explanation.actions?.map((action, index) => <li key={index}><span className="mr-2 text-violet-300">{index + 1}.</span>{action}</li>)}
          </ol>
          <div className="mt-3 text-[10px] uppercase tracking-wider text-slate-600">{explanation.model}</div>
        </div>
      )}
    </article>
  );
}
