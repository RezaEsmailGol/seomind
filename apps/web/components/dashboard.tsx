"use client";

import { useEffect, useMemo, useState } from "react";
import { Bot, CalendarDays, Database, Loader2, RefreshCw, Search, ShieldCheck } from "lucide-react";
import { api, type Audit, type SetupStatus } from "@/lib/api";
import type { Copy, Lang } from "@/lib/i18n";
import OpportunityCard from "./opportunity-card";
import StatCard from "./stat-card";
import TrendChart from "./trend-chart";
import UrlInspector from "./url-inspector";

function formatNumber(value: number) { return new Intl.NumberFormat("en-US", { notation: value >= 100000 ? "compact" : "standard", maximumFractionDigits: 1 }).format(value); }

export default function Dashboard({ lang, copy, status }: { lang: Lang; copy: Copy; status: SetupStatus }) {
  const [audit, setAudit] = useState<Audit | null>(null);
  const [loading, setLoading] = useState(true);
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.latestAudit().then(setAudit).catch(() => setAudit(null)).finally(() => setLoading(false));
  }, []);

  async function runAudit() {
    setImporting(true); setError(null);
    try { setAudit(await api.importAudit()); }
    catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setImporting(false); }
  }

  const metrics = useMemo(() => audit ? [
    { label: copy.clicks, value: formatNumber(audit.summary.current.clicks), delta: audit.summary.delta.clicks },
    { label: copy.impressions, value: formatNumber(audit.summary.current.impressions), delta: audit.summary.delta.impressions },
    { label: copy.ctr, value: `${(audit.summary.current.ctr * 100).toFixed(2)}%`, delta: audit.summary.delta.ctr },
    { label: copy.position, value: audit.summary.current.position.toFixed(1), delta: audit.summary.delta.position },
  ] : [], [audit, copy]);

  return (
    <div className="mx-auto max-w-7xl px-4 pb-16 pt-7 sm:px-6 lg:px-8">
      <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2"><span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-400/20 bg-emerald-400/10 px-3 py-1 text-xs font-bold text-emerald-200"><ShieldCheck className="h-3.5 w-3.5" />{copy.selectedProperty}</span><span className="text-xs text-slate-500">{status.selected_property}</span></div>
          <h1 className="mt-3 text-3xl font-black tracking-tight md:text-4xl">{copy.dashboard}</h1>
          <p className="mt-2 text-sm text-slate-500">{audit ? `${audit.period.start} → ${audit.period.end}` : copy.noAudit}</p>
        </div>
        <button onClick={runAudit} disabled={importing} className="inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-sky-400 to-cyan-300 px-5 py-3 text-sm font-black text-slate-950 transition hover:brightness-110 disabled:opacity-60">{importing ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}{importing ? copy.importing : copy.importAudit}</button>
      </div>

      {error && <div className="mb-5 rounded-2xl border border-rose-400/20 bg-rose-400/10 p-4 text-sm text-rose-200">{error}</div>}

      {loading ? <div className="flex min-h-[440px] items-center justify-center"><Loader2 className="h-7 w-7 animate-spin text-sky-300" /></div> : !audit ? (
        <div className="glass rounded-[28px] px-6 py-16 text-center"><div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl border border-sky-400/20 bg-sky-400/10"><Database className="h-7 w-7 text-sky-300" /></div><h2 className="mt-5 text-2xl font-black">{copy.noAudit}</h2><p className="mx-auto mt-2 max-w-xl text-sm leading-7 text-slate-500">{lang === "fa" ? "اولین Import داده، خلاصه عملکرد، نمودار روند و Opportunity Engine را فعال می‌کند." : "Your first import creates the performance summary, trend chart and deterministic opportunity queue."}</p><button onClick={runAudit} disabled={importing} className="mt-6 inline-flex items-center gap-2 rounded-xl bg-white px-5 py-3 text-sm font-black text-slate-950"><RefreshCw className="h-4 w-4" />{copy.importAudit}</button></div>
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{metrics.map((metric) => <StatCard key={metric.label} {...metric} />)}</div>

          <div className="mt-6 grid gap-6 xl:grid-cols-[1.4fr_.6fr]">
            <section className="glass rounded-3xl p-5 md:p-6"><div className="mb-5 flex items-center justify-between gap-3"><div><h2 className="text-lg font-black">{copy.trend}</h2><div className="mt-1 text-xs text-slate-500">{copy.clicks} · {audit.period.days} days</div></div><CalendarDays className="h-5 w-5 text-sky-300" /></div><TrendChart points={audit.trend} /></section>
            <section className="glass rounded-3xl p-5 md:p-6"><div className="flex items-center justify-between"><div><h2 className="text-lg font-black">SeoMind Engine</h2><div className="mt-1 text-xs text-slate-500">{audit.rows_analyzed.toLocaleString()} {copy.rowsAnalyzed}</div></div><Search className="h-5 w-5 text-violet-300" /></div><div className="mt-6 grid grid-cols-2 gap-3"><div className="rounded-2xl border border-white/[0.06] bg-slate-950/30 p-4"><div className="text-xs text-slate-500">{copy.opportunities}</div><div className="mt-2 text-3xl font-black text-white">{audit.opportunities.length}</div></div><div className="rounded-2xl border border-white/[0.06] bg-slate-950/30 p-4"><div className="text-xs text-slate-500">Local AI</div><div className={`mt-2 flex items-center gap-2 text-sm font-black ${status.ollama.available ? "text-emerald-300" : "text-slate-500"}`}><Bot className="h-4 w-4" />{status.ollama.available ? copy.ready : copy.optional}</div></div></div><p className="mt-5 text-xs leading-6 text-slate-600">{audit.data_note}</p></section>
          </div>

          <section className="mt-6"><div className="mb-4 flex items-end justify-between gap-4"><div><h2 className="text-2xl font-black">{copy.opportunities}</h2><p className="mt-1 text-sm text-slate-500">{copy.opportunityHint}</p></div></div><div className="grid gap-4 lg:grid-cols-2">{audit.opportunities.map((item) => <OpportunityCard key={item.id} item={item} lang={lang} labels={copy.types[item.kind]} reason={copy.reasons[item.kind]} aiAvailable={status.ollama.available} />)}</div>{audit.opportunities.length === 0 && <div className="glass rounded-2xl p-8 text-center text-sm text-slate-500">{lang === "fa" ? "در این بازه Opportunity معناداری با قوانین فعلی پیدا نشد." : "No material opportunities matched the current deterministic rules."}</div>}</section>

          <div className="mt-7"><UrlInspector lang={lang} title={copy.inspectTitle} body={copy.inspectBody} placeholder={copy.inspectPlaceholder} button={copy.inspectButton} /></div>
        </>
      )}
    </div>
  );
}
