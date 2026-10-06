import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";

export default function StatCard({ label, value, delta, suffix = "" }: { label: string; value: string; delta: number | null; suffix?: string }) {
  const good = delta !== null && delta > 0;
  const bad = delta !== null && delta < 0;
  return (
    <div className="glass soft-ring rounded-2xl p-5">
      <div className="text-sm font-medium text-slate-400">{label}</div>
      <div className="mt-3 flex items-end justify-between gap-3">
        <div className="text-3xl font-black tracking-tight text-white">{value}<span className="ml-1 text-base font-bold text-slate-500">{suffix}</span></div>
        <div className={`mb-1 inline-flex items-center gap-1 text-xs font-bold ${good ? "text-emerald-300" : bad ? "text-rose-300" : "text-slate-500"}`}>
          {good ? <ArrowUpRight className="h-4 w-4" /> : bad ? <ArrowDownRight className="h-4 w-4" /> : <Minus className="h-4 w-4" />}
          {delta === null ? "—" : `${Math.abs(delta).toFixed(1)}%`}
        </div>
      </div>
    </div>
  );
}
