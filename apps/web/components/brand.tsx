import { BrainCircuit, Search } from "lucide-react";

export default function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <div className="flex items-center gap-3">
      <div className="relative flex h-11 w-11 items-center justify-center rounded-2xl border border-sky-300/20 bg-gradient-to-br from-sky-400/20 via-cyan-400/10 to-violet-500/20 shadow-glow">
        <BrainCircuit className="h-6 w-6 text-sky-200" />
        <div className="absolute -bottom-1 -right-1 flex h-5 w-5 items-center justify-center rounded-lg border border-slate-800 bg-slate-950">
          <Search className="h-3 w-3 text-violet-300" />
        </div>
      </div>
      <div>
        <div className="text-lg font-black tracking-tight">SeoMind</div>
        {!compact && <div className="text-[11px] font-medium uppercase tracking-[.18em] text-slate-500">Local SEO Intelligence</div>}
      </div>
    </div>
  );
}
