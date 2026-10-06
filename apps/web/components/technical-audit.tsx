"use client";

import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  FileSearch,
  Gauge,
  Heading1,
  Link2,
  Loader2,
  Map,
  Network,
  RefreshCw,
  SearchCheck,
  Tags,
  TextSearch,
  XCircle,
} from "lucide-react";
import { api, type TechnicalAudit, type TechnicalIssue, type TechnicalPage } from "@/lib/api";
import type { Lang } from "@/lib/i18n";

const labels = {
  en: {
    title: "Technical SEO Audit",
    body: "Discover sitemaps, crawl pages safely, inspect Title/H1/Canonical and compare real Search Console queries with on-page content.",
    run: "Run technical audit",
    running: "Crawling and matching…",
    pages: "Crawl limit",
    crawled: "Pages crawled",
    score: "Average score",
    sitemaps: "Sitemap URLs",
    mismatch: "Query mismatches",
    errors: "Pages with errors",
    healthy: "Healthy pages",
    discovered: "Discovered sitemaps",
    pageResults: "Page audit",
    all: "All",
    issuesOnly: "With issues",
    mismatchOnly: "Query mismatch",
    technical: "Technical",
    queryMatch: "Query ↔ Content",
    titleTag: "Title",
    h1: "H1",
    canonical: "Canonical",
    meta: "Meta description",
    words: "Words",
    links: "Internal links",
    queries: "Top Search Console queries",
    noQueries: "No Search Console query rows matched this crawled URL.",
    missingTerms: "Missing terms",
    matchedIn: "Matched in",
    noAudit: "No technical audit yet. Run one to crawl the selected Search Console property.",
    noPages: "No pages match this filter.",
    updated: "Latest local audit",
    show: "Details",
    hide: "Hide",
    issueNames: {
      http_status: "HTTP status",
      missing_title: "Missing title",
      short_title: "Short title",
      long_title: "Long title",
      missing_h1: "Missing H1",
      multiple_h1: "Multiple H1",
      missing_canonical: "Missing canonical",
      canonical_outside_property: "Canonical outside property",
      canonical_points_elsewhere: "Canonical points elsewhere",
      noindex: "Noindex",
      missing_meta_description: "Missing meta description",
      thin_content: "Thin content",
      query_content_mismatch: "Query/content mismatch",
      robots_blocked: "Blocked by robots.txt",
      crawl_error: "Crawl error",
      non_html: "Non-HTML URL",
    } as Record<string, string>,
  },
  fa: {
    title: "ممیزی فنی سئو",
    body: "Sitemapها را پیدا می‌کند، صفحات را به‌صورت امن Crawl می‌کند، Title/H1/Canonical را بررسی می‌کند و Queryهای واقعی Search Console را با محتوای صفحه تطبیق می‌دهد.",
    run: "اجرای ممیزی فنی",
    running: "در حال Crawl و تطبیق…",
    pages: "تعداد صفحات",
    crawled: "صفحات Crawl شده",
    score: "میانگین امتیاز",
    sitemaps: "URLهای Sitemap",
    mismatch: "عدم تطبیق Query",
    errors: "صفحات دارای خطا",
    healthy: "صفحات سالم",
    discovered: "Sitemapهای شناسایی‌شده",
    pageResults: "بررسی صفحات",
    all: "همه",
    issuesOnly: "دارای مشکل",
    mismatchOnly: "عدم تطبیق Query",
    technical: "فنی",
    queryMatch: "تطبیق Query ↔ محتوا",
    titleTag: "Title",
    h1: "H1",
    canonical: "Canonical",
    meta: "Meta Description",
    words: "کلمات",
    links: "لینک داخلی",
    queries: "Queryهای برتر Search Console",
    noQueries: "برای این URL داده Query قابل تطبیقی از Search Console پیدا نشد.",
    missingTerms: "عبارت‌های غایب",
    matchedIn: "محل تطبیق",
    noAudit: "هنوز ممیزی فنی انجام نشده است. برای Property انتخاب‌شده یک Crawl اجرا کنید.",
    noPages: "صفحه‌ای با این فیلتر پیدا نشد.",
    updated: "آخرین ممیزی محلی",
    show: "جزئیات",
    hide: "بستن",
    issueNames: {
      http_status: "خطای HTTP",
      missing_title: "Title وجود ندارد",
      short_title: "Title کوتاه",
      long_title: "Title طولانی",
      missing_h1: "H1 وجود ندارد",
      multiple_h1: "چند H1",
      missing_canonical: "Canonical وجود ندارد",
      canonical_outside_property: "Canonical خارج از Property",
      canonical_points_elsewhere: "Canonical به URL دیگری اشاره می‌کند",
      noindex: "Noindex",
      missing_meta_description: "Meta Description وجود ندارد",
      thin_content: "محتوای کم",
      query_content_mismatch: "عدم تطبیق Query و محتوا",
      robots_blocked: "مسدود توسط robots.txt",
      crawl_error: "خطای Crawl",
      non_html: "URL غیر HTML",
    } as Record<string, string>,
  },
} as const;

function scoreClass(score: number) {
  if (score >= 85) return "text-emerald-300 border-emerald-400/20 bg-emerald-400/10";
  if (score >= 65) return "text-amber-200 border-amber-400/20 bg-amber-400/10";
  return "text-rose-200 border-rose-400/20 bg-rose-400/10";
}

function severityClass(issue: TechnicalIssue) {
  if (issue.severity === "error") return "border-rose-400/20 bg-rose-400/10 text-rose-200";
  if (issue.severity === "warning") return "border-amber-400/20 bg-amber-400/10 text-amber-200";
  return "border-sky-400/15 bg-sky-400/[0.07] text-sky-200";
}

function PageAuditCard({ page, lang }: { page: TechnicalPage; lang: Lang }) {
  const t = labels[lang];
  const [open, setOpen] = useState(false);
  const queryScore = page.content_match_score;

  return (
    <article className="glass overflow-hidden rounded-2xl">
      <div className="p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className={`rounded-full border px-2.5 py-1 text-xs font-black ${scoreClass(page.technical_score)}`}>
                {t.technical}: {page.technical_score}/100
              </span>
              {queryScore !== null && queryScore !== undefined && (
                <span className={`rounded-full border px-2.5 py-1 text-xs font-black ${scoreClass(queryScore)}`}>
                  {t.queryMatch}: {queryScore}/100
                </span>
              )}
              <span className="rounded-full border border-white/10 bg-white/[0.04] px-2.5 py-1 text-xs font-bold text-slate-400">
                HTTP {page.status ?? "—"}
              </span>
            </div>
            <a href={page.url} target="_blank" rel="noreferrer" className="mt-3 block truncate text-sm font-bold text-sky-200 hover:text-sky-100" title={page.url}>
              {page.url}
            </a>
            <div className="mt-2 truncate text-base font-black text-white" title={page.title || ""}>
              {page.title || (lang === "fa" ? "بدون Title" : "No title")}
            </div>
          </div>
          <button onClick={() => setOpen(!open)} className="inline-flex shrink-0 items-center gap-2 rounded-xl border border-white/10 bg-white/[0.035] px-3 py-2 text-xs font-bold text-slate-300 hover:bg-white/[0.06]">
            {open ? t.hide : t.show}
            {open ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </button>
        </div>

        {!!page.issues?.length && (
          <div className="mt-4 flex flex-wrap gap-2">
            {page.issues.map((issue, index) => (
              <span key={`${issue.code}-${index}`} className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-[11px] font-bold ${severityClass(issue)}`}>
                {issue.severity === "error" ? <XCircle className="h-3.5 w-3.5" /> : issue.severity === "warning" ? <AlertTriangle className="h-3.5 w-3.5" /> : <SearchCheck className="h-3.5 w-3.5" />}
                {t.issueNames[issue.code] || issue.code}
              </span>
            ))}
          </div>
        )}
      </div>

      {open && (
        <div className="border-t border-white/[0.06] bg-slate-950/25 p-5">
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            <Info icon={Tags} label={t.titleTag} value={page.title || "—"} meta={page.title_length !== undefined ? `${page.title_length} chars` : undefined} />
            <Info icon={Heading1} label={t.h1} value={page.h1?.[0] || "—"} meta={page.h1_count !== undefined ? `${page.h1_count} H1` : undefined} />
            <Info icon={Link2} label={t.canonical} value={page.canonical || "—"} />
            <Info icon={TextSearch} label={t.meta} value={page.meta_description || "—"} meta={page.meta_description_length !== undefined ? `${page.meta_description_length} chars` : undefined} />
          </div>

          <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Mini label={t.words} value={(page.word_count ?? 0).toLocaleString()} />
            <Mini label={t.links} value={(page.internal_links ?? 0).toLocaleString()} />
            <Mini label="Response" value={page.response_time_ms ? `${page.response_time_ms} ms` : "—"} />
            <Mini label="Robots" value={page.noindex ? "noindex" : (page.meta_robots || "index")} />
          </div>

          <div className="mt-5">
            <div className="mb-3 text-xs font-black uppercase tracking-[.14em] text-slate-500">{t.queries}</div>
            {page.query_matches?.length ? (
              <div className="space-y-3">
                {page.query_matches.slice(0, 5).map((query) => (
                  <div key={query.query} className="rounded-xl border border-white/[0.06] bg-slate-950/35 p-4">
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                      <div className="font-bold text-slate-200">{query.query}</div>
                      <span className={`shrink-0 rounded-full border px-2.5 py-1 text-xs font-black ${scoreClass(query.score)}`}>{query.score}/100</span>
                    </div>
                    <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-white/[0.06]">
                      <div className={`h-full rounded-full ${query.score >= 85 ? "bg-emerald-400" : query.score >= 65 ? "bg-amber-300" : "bg-rose-400"}`} style={{ width: `${query.score}%` }} />
                    </div>
                    <div className="mt-3 flex flex-wrap gap-x-4 gap-y-2 text-[11px] text-slate-500">
                      <span>Impr. {query.impressions.toLocaleString()}</span>
                      <span>Clicks {query.clicks.toLocaleString()}</span>
                      <span>Pos. {query.position.toFixed(1)}</span>
                      <span>{t.matchedIn}: {query.matched_in.length ? query.matched_in.join(", ") : "—"}</span>
                      {!!query.missing_terms.length && <span className="text-amber-300/80">{t.missingTerms}: {query.missing_terms.join(", ")}</span>}
                    </div>
                  </div>
                ))}
              </div>
            ) : <div className="rounded-xl border border-dashed border-white/10 p-5 text-sm text-slate-500">{t.noQueries}</div>}
          </div>
        </div>
      )}
    </article>
  );
}

function Info({ icon: Icon, label, value, meta }: { icon: typeof Tags; label: string; value: string; meta?: string }) {
  return (
    <div className="min-w-0 rounded-xl border border-white/[0.06] bg-slate-950/35 p-4">
      <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-wider text-slate-600"><Icon className="h-3.5 w-3.5" />{label}</div>
      <div className="mt-2 line-clamp-3 break-words text-xs font-semibold leading-5 text-slate-300" title={value}>{value}</div>
      {meta && <div className="mt-2 text-[10px] text-slate-600">{meta}</div>}
    </div>
  );
}

function Mini({ label, value }: { label: string; value: string }) {
  return <div className="rounded-xl border border-white/[0.05] bg-white/[0.02] p-3"><div className="text-[10px] uppercase tracking-wider text-slate-600">{label}</div><div className="mt-1 text-sm font-black text-slate-300">{value}</div></div>;
}

export default function TechnicalAuditPanel({ lang }: { lang: Lang }) {
  const t = labels[lang];
  const [audit, setAudit] = useState<TechnicalAudit | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [maxPages, setMaxPages] = useState(50);
  const [filter, setFilter] = useState<"all" | "issues" | "mismatch">("all");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.latestTechnicalAudit().then(setAudit).catch(() => setAudit(null)).finally(() => setLoading(false));
  }, []);

  async function run() {
    setRunning(true); setError(null);
    try { setAudit(await api.technicalAudit(maxPages)); }
    catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setRunning(false); }
  }

  const pages = useMemo(() => {
    if (!audit) return [];
    if (filter === "issues") return audit.pages.filter((page) => page.issues?.length);
    if (filter === "mismatch") return audit.pages.filter((page) => page.issues?.some((issue) => issue.code === "query_content_mismatch"));
    return audit.pages;
  }, [audit, filter]);

  return (
    <section className="mt-8">
      <div className="glass rounded-[28px] p-6 md:p-7">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border border-violet-400/20 bg-violet-400/10"><FileSearch className="h-6 w-6 text-violet-200" /></div>
            <div><h2 className="text-2xl font-black">{t.title}</h2><p className="mt-2 max-w-3xl text-sm leading-7 text-slate-400">{t.body}</p></div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <label className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-slate-950/30 px-3 py-2.5 text-xs font-bold text-slate-400">
              {t.pages}
              <select value={maxPages} onChange={(e) => setMaxPages(Number(e.target.value))} className="bg-transparent font-black text-white outline-none">
                {[25, 50, 100, 200].map((value) => <option key={value} value={value} className="bg-slate-900">{value}</option>)}
              </select>
            </label>
            <button onClick={run} disabled={running} className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-violet-400 to-sky-300 px-4 py-2.5 text-xs font-black text-slate-950 transition hover:brightness-110 disabled:opacity-50">
              {running ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
              {running ? t.running : t.run}
            </button>
          </div>
        </div>

        {error && <div className="mt-5 rounded-xl border border-rose-400/20 bg-rose-400/10 p-4 text-sm text-rose-200">{error}</div>}

        {loading ? <div className="flex h-48 items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-violet-300" /></div> : !audit ? (
          <div className="mt-7 rounded-2xl border border-dashed border-white/10 p-10 text-center">
            <Network className="mx-auto h-8 w-8 text-slate-600" />
            <div className="mt-3 text-sm text-slate-500">{t.noAudit}</div>
          </div>
        ) : (
          <>
            <div className="mt-7 grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
              <Summary icon={FileSearch} label={t.crawled} value={audit.summary.pages_crawled} />
              <Summary icon={Gauge} label={t.score} value={audit.summary.average_score} suffix="/100" />
              <Summary icon={Map} label={t.sitemaps} value={audit.sitemap_url_count} />
              <Summary icon={AlertTriangle} label={t.mismatch} value={audit.summary.pages_with_query_mismatch} />
              <Summary icon={XCircle} label={t.errors} value={audit.summary.pages_with_errors} />
              <Summary icon={CheckCircle2} label={t.healthy} value={audit.summary.healthy_pages} />
            </div>

            {!!audit.sitemaps.length && (
              <div className="mt-6">
                <div className="mb-3 flex items-center gap-2 text-xs font-black uppercase tracking-[.14em] text-slate-500"><Map className="h-4 w-4" />{t.discovered}</div>
                <div className="flex flex-wrap gap-2">{audit.sitemaps.map((url) => <span key={url} className="max-w-full truncate rounded-lg border border-white/[0.06] bg-slate-950/35 px-3 py-2 text-[11px] text-slate-400" title={url}>{url}</span>)}</div>
              </div>
            )}
          </>
        )}
      </div>

      {audit && (
        <div className="mt-6">
          <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div><h3 className="text-xl font-black">{t.pageResults}</h3><div className="mt-1 text-xs text-slate-600">{audit.period.start} → {audit.period.end} · {audit.gsc_rows_analyzed.toLocaleString()} GSC rows</div></div>
            <div className="inline-flex self-start rounded-xl border border-white/10 bg-white/[0.03] p-1">
              {([["all", t.all], ["issues", t.issuesOnly], ["mismatch", t.mismatchOnly]] as const).map(([key, label]) => <button key={key} onClick={() => setFilter(key)} className={`rounded-lg px-3 py-2 text-xs font-bold transition ${filter === key ? "bg-white text-slate-950" : "text-slate-500 hover:text-white"}`}>{label}</button>)}
            </div>
          </div>
          <div className="space-y-4">{pages.map((page) => <PageAuditCard key={page.url} page={page} lang={lang} />)}{!pages.length && <div className="glass rounded-2xl p-8 text-center text-sm text-slate-500">{t.noPages}</div>}</div>
        </div>
      )}
    </section>
  );
}

function Summary({ icon: Icon, label, value, suffix = "" }: { icon: typeof FileSearch; label: string; value: number; suffix?: string }) {
  return <div className="rounded-2xl border border-white/[0.06] bg-slate-950/30 p-4"><Icon className="h-4 w-4 text-sky-300" /><div className="mt-3 text-2xl font-black">{value}{suffix && <span className="text-xs text-slate-600">{suffix}</span>}</div><div className="mt-1 text-[11px] text-slate-500">{label}</div></div>;
}
