"use client";

import { useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  Bot,
  Check,
  CheckCircle2,
  CloudCog,
  FileJson2,
  Gauge,
  HardDrive,
  KeyRound,
  LaptopMinimalCheck,
  Loader2,
  LockKeyhole,
  Rocket,
  SearchCheck,
  ServerCog,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { API_URL, api, type PropertyItem, type SetupStatus } from "@/lib/api";
import type { Copy, Lang } from "@/lib/i18n";
import StatusPill from "./status-pill";

const icons = [Rocket, LaptopMinimalCheck, KeyRound, SearchCheck, Bot, CheckCircle2];

export default function SetupWizard({ lang, copy, status, refresh, onComplete }: { lang: Lang; copy: Copy; status: SetupStatus; refresh: () => Promise<void>; onComplete: () => void }) {
  const [step, setStep] = useState(0);
  const [properties, setProperties] = useState<PropertyItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedCredentials, setSavedCredentials] = useState(status.steps.google_credentials);
  const [redirectUri, setRedirectUri] = useState("http://127.0.0.1:8787/api/google/oauth/callback");

  useEffect(() => {
    if (status.ready) setStep(5);
    else if (status.steps.google_oauth && !status.steps.search_console) setStep(3);
    else if (status.steps.google_credentials && !status.steps.google_oauth) setStep(2);
  }, [status]);

  const Icon = icons[step];
  const rtl = lang === "fa";
  const BackIcon = rtl ? ArrowRight : ArrowLeft;
  const NextIcon = rtl ? ArrowLeft : ArrowRight;

  const progress = useMemo(() => ((step + 1) / copy.steps.length) * 100, [step, copy.steps.length]);

  async function readCredentials(file?: File) {
    if (!file) return;
    setLoading(true); setError(null);
    try {
      const parsed = JSON.parse(await file.text()) as Record<string, unknown>;
      const result = await api.saveCredentials(parsed);
      setSavedCredentials(true);
      setRedirectUri(result.redirect_uri);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally { setLoading(false); }
  }

  async function loadProperties() {
    setLoading(true); setError(null);
    try { setProperties((await api.properties()).items); }
    catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setLoading(false); }
  }

  async function chooseProperty(siteUrl: string) {
    setLoading(true); setError(null);
    try {
      await api.selectProperty(siteUrl);
      await refresh();
      setStep(4);
    } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setLoading(false); }
  }

  const systemRows = [
    { icon: ServerCog, title: "FastAPI", ok: status.steps.runtime, optional: false },
    { icon: HardDrive, title: lang === "fa" ? "ذخیره‌سازی محلی" : "Local storage", ok: status.steps.local_storage, optional: false },
    { icon: ShieldCheck, title: lang === "fa" ? "فایل OAuth" : "OAuth credentials", ok: status.steps.google_credentials, optional: false },
    { icon: Bot, title: "Ollama", ok: status.ollama.available, optional: true },
  ];

  return (
    <div className="mx-auto max-w-6xl px-4 pb-14 pt-8 sm:px-6 lg:px-8">
      <div className="mb-7 grid grid-cols-6 gap-2">
        {copy.steps.map((label, index) => {
          const done = index < step;
          const current = index === step;
          return (
            <button key={label} type="button" onClick={() => index <= step && setStep(index)} className="group text-start">
              <div className={`h-1.5 rounded-full transition ${done ? "bg-emerald-400" : current ? "bg-gradient-to-r from-sky-400 to-violet-400" : "bg-white/[0.07]"}`} />
              <div className={`mt-2 hidden text-[11px] font-bold sm:block ${current ? "text-white" : done ? "text-emerald-300" : "text-slate-600"}`}>{label}</div>
            </button>
          );
        })}
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <main className="glass rounded-[28px] p-6 md:p-8">
          <div className="flex items-start gap-4">
            <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl border border-sky-300/20 bg-gradient-to-br from-sky-400/20 to-violet-500/20">
              <Icon className="h-7 w-7 text-sky-200" />
            </div>
            <div className="min-w-0">
              <div className="text-xs font-bold uppercase tracking-[.18em] text-sky-300">{lang === "fa" ? `مرحله ${step + 1} از ۶` : `Step ${step + 1} of 6`}</div>
              <h1 className="mt-1 text-2xl font-black tracking-tight md:text-3xl">{copy.steps[step]}</h1>
            </div>
          </div>

          <div className="mt-7 h-1 overflow-hidden rounded-full bg-white/[0.06]"><div className="h-full rounded-full bg-gradient-to-r from-sky-400 via-cyan-300 to-violet-400 transition-all duration-500" style={{ width: `${progress}%` }} /></div>

          <div className="mt-8 min-h-[360px]">
            {step === 0 && (
              <div className="grid gap-7 md:grid-cols-[1fr_250px] md:items-center">
                <div>
                  <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-emerald-400/20 bg-emerald-400/10 px-3 py-1.5 text-xs font-bold text-emerald-200"><LockKeyhole className="h-3.5 w-3.5" />{copy.privateBadge}</div>
                  <h2 className="max-w-2xl text-3xl font-black leading-tight md:text-5xl"><span className="text-gradient">{copy.heroTitle}</span></h2>
                  <p className="mt-5 max-w-2xl text-base leading-8 text-slate-400">{copy.heroBody}</p>
                  <button onClick={() => setStep(1)} className="mt-7 inline-flex items-center gap-2 rounded-xl bg-white px-5 py-3 text-sm font-black text-slate-950 transition hover:bg-sky-100">{copy.start}<NextIcon className="h-4 w-4" /></button>
                </div>
                <div className="relative mx-auto h-56 w-56">
                  <div className="absolute inset-0 rounded-full bg-sky-400/10 blur-3xl" />
                  <div className="absolute inset-3 rounded-full border border-sky-300/10" />
                  <div className="absolute inset-10 rounded-full border border-violet-300/15" />
                  <div className="absolute inset-[72px] flex items-center justify-center rounded-3xl border border-white/10 bg-slate-950/60 shadow-glow"><Sparkles className="h-12 w-12 text-sky-200" /></div>
                </div>
              </div>
            )}

            {step === 1 && (
              <div>
                <h2 className="text-2xl font-black">{copy.systemTitle}</h2><p className="mt-2 max-w-2xl leading-7 text-slate-400">{copy.systemBody}</p>
                <div className="mt-6 grid gap-3 sm:grid-cols-2">
                  {systemRows.map((row) => <div key={row.title} className="rounded-2xl border border-white/[0.07] bg-slate-950/30 p-4"><div className="flex items-center justify-between gap-3"><div className="flex items-center gap-3"><div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/[0.04]"><row.icon className="h-5 w-5 text-sky-200" /></div><div className="font-bold">{row.title}</div></div><StatusPill ok={row.ok} label={row.ok ? copy.ready : row.optional ? copy.optional : copy.notConnected} /></div></div>)}
                </div>
              </div>
            )}

            {step === 2 && (
              <div>
                <h2 className="text-2xl font-black">{copy.googleTitle}</h2><p className="mt-2 max-w-3xl leading-7 text-slate-400">{copy.googleBody}</p>
                <div className="mt-6 rounded-2xl border border-white/[0.07] bg-slate-950/30 p-5">
                  <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"><div className="flex items-center gap-3"><div className="flex h-11 w-11 items-center justify-center rounded-xl bg-sky-400/10"><FileJson2 className="h-5 w-5 text-sky-300" /></div><div><div className="font-bold">client_secret.json</div><div className="mt-1 text-xs text-slate-500">{savedCredentials ? copy.jsonSaved : copy.chooseJson}</div></div></div><label className="cursor-pointer rounded-xl border border-white/10 bg-white/[0.04] px-4 py-2.5 text-center text-sm font-bold text-slate-200 transition hover:bg-white/[0.07]"><input type="file" accept="application/json,.json" className="hidden" onChange={(e) => readCredentials(e.target.files?.[0])} />{loading ? "…" : copy.chooseJson}</label></div>
                  <div className="mt-5 rounded-xl border border-amber-400/15 bg-amber-400/[0.06] p-4"><div className="text-xs font-bold uppercase tracking-wider text-amber-200">{copy.redirectUri}</div><code className="mt-2 block break-all text-xs text-slate-400">{redirectUri}</code></div>
                </div>
                <button disabled={!savedCredentials} onClick={() => { window.location.href = `${API_URL}/api/google/oauth/start`; }} className="mt-5 inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-sky-400 to-cyan-300 px-5 py-3 text-sm font-black text-slate-950 transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40"><CloudCog className="h-4 w-4" />{copy.connectGoogle}</button>
              </div>
            )}

            {step === 3 && (
              <div>
                <h2 className="text-2xl font-black">{copy.propertyTitle}</h2><p className="mt-2 max-w-2xl leading-7 text-slate-400">{copy.propertyBody}</p>
                <button onClick={loadProperties} disabled={loading} className="mt-5 inline-flex items-center gap-2 rounded-xl border border-sky-400/20 bg-sky-400/10 px-4 py-2.5 text-sm font-bold text-sky-200 transition hover:bg-sky-400/15"><SearchCheck className="h-4 w-4" />{loading ? copy.loading : copy.loadProperties}</button>
                <div className="mt-5 space-y-3">
                  {properties.map((item) => <div key={item.site_url} className="flex flex-col gap-3 rounded-2xl border border-white/[0.07] bg-slate-950/30 p-4 sm:flex-row sm:items-center sm:justify-between"><div className="min-w-0"><div className="truncate font-bold text-white" title={item.site_url}>{item.site_url}</div><div className="mt-1 text-xs text-slate-500">{item.permission}</div></div><button onClick={() => chooseProperty(item.site_url)} className="shrink-0 rounded-xl bg-white px-4 py-2.5 text-xs font-black text-slate-950 hover:bg-sky-100">{copy.useProperty}</button></div>)}
                  {!loading && properties.length === 0 && <div className="rounded-2xl border border-dashed border-white/10 p-7 text-center text-sm text-slate-500">{lang === "fa" ? "برای نمایش سایت‌ها، «دریافت پراپرتی‌ها» را بزنید." : "Load your Search Console properties to continue."}</div>}
                </div>
              </div>
            )}

            {step === 4 && (
              <div>
                <h2 className="text-2xl font-black">{copy.aiTitle}</h2><p className="mt-2 max-w-3xl leading-7 text-slate-400">{copy.aiBody}</p>
                <div className={`mt-6 rounded-2xl border p-5 ${status.ollama.available ? "border-emerald-400/20 bg-emerald-400/[0.07]" : "border-white/[0.07] bg-slate-950/30"}`}>
                  <div className="flex items-center gap-4"><div className={`flex h-12 w-12 items-center justify-center rounded-2xl ${status.ollama.available ? "bg-emerald-400/10" : "bg-white/[0.04]"}`}><Bot className={`h-6 w-6 ${status.ollama.available ? "text-emerald-300" : "text-slate-500"}`} /></div><div className="flex-1"><div className="font-black">{status.ollama.available ? copy.ollamaDetected : copy.ollamaMissing}</div><div className="mt-1 text-xs text-slate-500">{status.ollama.available && status.ollama.models.length ? status.ollama.models.join(" · ") : "http://127.0.0.1:11434"}</div></div><StatusPill ok={status.ollama.available} label={status.ollama.available ? copy.ready : copy.optional} /></div>
                </div>
                <button onClick={() => setStep(5)} className="mt-6 inline-flex items-center gap-2 rounded-xl bg-white px-5 py-3 text-sm font-black text-slate-950 hover:bg-sky-100">{copy.continue}<NextIcon className="h-4 w-4" /></button>
              </div>
            )}

            {step === 5 && (
              <div className="py-5 text-center">
                <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-[26px] border border-emerald-400/20 bg-emerald-400/10"><Check className="h-10 w-10 text-emerald-300" /></div>
                <h2 className="mt-6 text-3xl font-black">{copy.finishTitle}</h2><p className="mx-auto mt-3 max-w-2xl leading-7 text-slate-400">{copy.finishBody}</p>
                <button onClick={onComplete} className="mt-7 inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-sky-400 to-emerald-300 px-6 py-3 text-sm font-black text-slate-950 hover:brightness-110"><Gauge className="h-4 w-4" />{copy.done}</button>
              </div>
            )}
          </div>

          {error && <div className="mt-5 rounded-xl border border-rose-400/20 bg-rose-400/10 p-4 text-sm text-rose-200">{error}</div>}

          {step > 0 && step < 5 && (
            <div className="mt-7 flex items-center justify-between border-t border-white/[0.06] pt-5"><button onClick={() => setStep(Math.max(0, step - 1))} className="inline-flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-bold text-slate-400 hover:bg-white/[0.04] hover:text-white"><BackIcon className="h-4 w-4" />{copy.back}</button>{step === 1 && <button onClick={() => setStep(2)} className="inline-flex items-center gap-2 rounded-xl bg-white px-4 py-2.5 text-sm font-black text-slate-950 hover:bg-sky-100">{copy.continue}<NextIcon className="h-4 w-4" /></button>}</div>
          )}
        </main>

        <aside className="space-y-4">
          <div className="glass rounded-3xl p-5"><div className="text-xs font-bold uppercase tracking-[.18em] text-slate-500">{lang === "fa" ? "وضعیت راه‌اندازی" : "Setup status"}</div><div className="mt-4 space-y-3">{[
            [lang === "fa" ? "سیستم" : "System", status.steps.runtime],
            ["OAuth", status.steps.google_oauth],
            [lang === "fa" ? "پراپرتی" : "Property", status.steps.search_console],
            ["Ollama", status.ollama.available],
          ].map(([label, ok]) => <div key={String(label)} className="flex items-center justify-between gap-3 rounded-xl border border-white/[0.05] bg-white/[0.025] px-3 py-3"><span className="text-sm font-semibold text-slate-300">{String(label)}</span><StatusPill ok={Boolean(ok)} label={Boolean(ok) ? copy.ready : String(label) === "Ollama" ? copy.optional : copy.notConnected} /></div>)}</div></div>
          <div className="rounded-3xl border border-violet-400/15 bg-gradient-to-br from-violet-400/[0.08] to-sky-400/[0.04] p-5"><Sparkles className="h-5 w-5 text-violet-300" /><div className="mt-4 text-sm font-black">{lang === "fa" ? "AI تصمیم‌گیر نیست" : "AI is not the decision engine"}</div><p className="mt-2 text-xs leading-6 text-slate-500">{lang === "fa" ? "یافته‌های SeoMind با قوانین قابل‌تست ساخته می‌شوند. LLM فقط برای توضیح بهتر استفاده می‌شود." : "SeoMind finds issues with testable rules. The LLM is only an optional explanation layer."}</p></div>
        </aside>
      </div>
    </div>
  );
}
