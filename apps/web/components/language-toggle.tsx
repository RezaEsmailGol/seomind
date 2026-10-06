"use client";

import { Languages } from "lucide-react";
import type { Lang } from "@/lib/i18n";

export default function LanguageToggle({ lang, onChange }: { lang: Lang; onChange: (lang: Lang) => void }) {
  const next = lang === "en" ? "fa" : "en";
  return (
    <button
      type="button"
      onClick={() => onChange(next)}
      className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.045] px-3.5 py-2.5 text-sm font-semibold text-slate-200 transition hover:border-sky-400/30 hover:bg-sky-400/10"
      aria-label="Change language"
    >
      <Languages className="h-4 w-4 text-sky-300" />
      {lang === "en" ? "فارسی" : "EN"}
    </button>
  );
}
