"use client";

import type { Audit } from "@/lib/api";

export default function TrendChart({ points }: { points: Audit["trend"] }) {
  if (!points.length) {
    return <div className="flex h-56 items-center justify-center text-sm text-slate-500">No trend data</div>;
  }

  const width = 900;
  const height = 240;
  const pad = 18;
  const values = points.map((p) => p.clicks);
  const max = Math.max(...values, 1);
  const min = Math.min(...values, 0);
  const range = Math.max(max - min, 1);
  const x = (index: number) => pad + (index / Math.max(points.length - 1, 1)) * (width - pad * 2);
  const y = (value: number) => height - pad - ((value - min) / range) * (height - pad * 2);
  const line = points.map((p, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(p.clicks).toFixed(1)}`).join(" ");
  const area = `${line} L${x(points.length - 1)},${height - pad} L${x(0)},${height - pad} Z`;

  return (
    <div className="overflow-hidden rounded-2xl border border-white/[0.06] bg-slate-950/30 p-3">
      <svg viewBox={`0 0 ${width} ${height}`} className="h-56 w-full" role="img" aria-label="Clicks trend">
        <defs>
          <linearGradient id="chartFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#38bdf8" stopOpacity=".30" />
            <stop offset="1" stopColor="#38bdf8" stopOpacity="0" />
          </linearGradient>
          <linearGradient id="chartLine" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0" stopColor="#38bdf8" />
            <stop offset="1" stopColor="#a78bfa" />
          </linearGradient>
        </defs>
        {[0.25, 0.5, 0.75].map((v) => (
          <line key={v} x1={pad} x2={width - pad} y1={height * v} y2={height * v} stroke="rgba(148,163,184,.10)" strokeWidth="1" />
        ))}
        <path d={area} fill="url(#chartFill)" />
        <path d={line} fill="none" stroke="url(#chartLine)" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
        {points.map((p, i) => (
          <circle key={p.date} cx={x(i)} cy={y(p.clicks)} r="3" fill="#e0f2fe" opacity={i % Math.ceil(points.length / 12) === 0 ? 1 : .45} />
        ))}
      </svg>
      <div className="flex justify-between px-2 text-[11px] text-slate-500">
        <span>{points[0]?.date}</span>
        <span>{points[points.length - 1]?.date}</span>
      </div>
    </div>
  );
}
