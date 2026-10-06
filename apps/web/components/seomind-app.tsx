"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Github, Loader2, Settings2 } from "lucide-react";
import { api, type SetupStatus } from "@/lib/api";
import { text, type Lang } from "@/lib/i18n";
import Brand from "./brand";
import Dashboard from "./dashboard";
import LanguageToggle from "./language-toggle";
import SetupWizard from "./setup-wizard";

const emptyStatus: SetupStatus = {
  ready: false,
  next: "google_credentials",
  selected_property: null,
  steps: { runtime: false, local_storage: false, google_credentials: false, google_oauth: false, search_console: false, ollama: false },
  ollama: { available: false, models: [] },
};

export default function SeoMindApp() {
  const [lang, setLang] = useState<Lang>("en");
  const [status, setStatus] = useState<SetupStatus>(emptyStatus);
  const [loading, setLoading] = useState(true);
  const [showSetup, setShowSetup] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const copy = useMemo(() => text[lang], [lang]);

  const refresh = useCallback(async () => {
    try { setStatus(await api.setup()); setError(null); }
    catch (e) { setError(e instanceof Error ? e.message : String(e)); }
  }, []);

  useEffect(() => {
    const saved = window.localStorage.getItem("seomind-lang") as Lang | null;
    if (saved === "fa" || saved === "en") setLang(saved);
    refresh().finally(() => setLoading(false));
  }, [refresh]);

  useEffect(() => {
    document.documentElement.lang = lang;
    document.documentElement.dir = lang === "fa" ? "rtl" : "ltr";
    window.localStorage.setItem("seomind-lang", lang);
  }, [lang]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("google") === "connected") {
      setShowSetup(true);
      refresh();
      window.history.replaceState({}, "", window.location.pathname);
    }
    const message = params.get("message");
    if (params.get("google") === "error" && message) setError(message);
  }, [refresh]);

  async function disconnect() {
    await api.disconnect();
    await refresh();
    setShowSetup(true);
  }

  if (loading) return <div className="grid-noise flex min-h-screen items-center justify-center"><Loader2 className="h-8 w-8 animate-spin text-sky-300" /></div>;

  const setupMode = showSetup || !status.ready;

  return (
    <div className="grid-noise min-h-screen" dir={lang === "fa" ? "rtl" : "ltr"}>
      <header className="sticky top-0 z-40 border-b border-white/[0.06] bg-[#060b14]/75 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3 sm:px-6 lg:px-8">
          <Brand />
          <div className="flex items-center gap-2">
            {status.ready && <button onClick={() => setShowSetup(!showSetup)} className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-white/10 bg-white/[0.035] text-slate-400 transition hover:text-white" title={copy.setup}><Settings2 className="h-4 w-4" /></button>}
            <a href="https://github.com/RezaEsmailGol/seomind" target="_blank" rel="noreferrer" className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-white/10 bg-white/[0.035] text-slate-400 transition hover:text-white" aria-label="GitHub"><Github className="h-4 w-4" /></a>
            <LanguageToggle lang={lang} onChange={setLang} />
          </div>
        </div>
      </header>

      {error && <div className="mx-auto mt-5 max-w-7xl px-4 sm:px-6 lg:px-8"><div className="rounded-xl border border-rose-400/20 bg-rose-400/10 p-4 text-sm text-rose-200">{error}</div></div>}

      {setupMode ? <SetupWizard lang={lang} copy={copy} status={status} refresh={refresh} onComplete={async () => { await refresh(); setShowSetup(false); }} /> : <Dashboard lang={lang} copy={copy} status={status} />}

      <footer className="border-t border-white/[0.05] py-8 text-center text-xs text-slate-600"><div>SeoMind · Open source · Local-first</div>{status.ready && <button onClick={disconnect} className="mt-2 text-slate-600 hover:text-rose-300">{copy.disconnect}</button>}</footer>
    </div>
  );
}
