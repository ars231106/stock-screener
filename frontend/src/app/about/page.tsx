import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "About",
  description: "Who built this stock screener and how it works.",
};

export default function AboutPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-16 sm:px-6">
      <h1 className="section-title">About</h1>
      <p className="muted mt-4 leading-relaxed">
        This platform was built by Aryan Surani to explore Indian and global
        equities through a clean, fast interface — search a company, read its
        fundamentals, run a screen, keep a watchlist.
      </p>

      <h2 className="mt-10 text-lg font-semibold text-slate-900 dark:text-slate-100">
        How it is put together
      </h2>
      <ul className="muted mt-4 space-y-2 leading-relaxed">
        <li>
          <strong className="text-slate-700 dark:text-slate-200">Frontend</strong> —
          Next.js App Router with Tailwind, deployed on Vercel.
        </li>
        <li>
          <strong className="text-slate-700 dark:text-slate-200">Backend</strong> —
          FastAPI on Render, which proxies and caches market data so the
          provider key never reaches the browser.
        </li>
        <li>
          <strong className="text-slate-700 dark:text-slate-200">Database</strong> —
          Supabase Postgres for accounts, watchlists, saved screens and the
          shared quote cache, with row-level security on every user table.
        </li>
      </ul>

      <h2
        id="support"
        className="mt-10 scroll-mt-24 text-lg font-semibold text-slate-900 dark:text-slate-100"
      >
        Support
      </h2>
      <p className="muted mt-4 leading-relaxed">
        Found a bug or want a metric added? Open an issue on the GitHub
        repository and describe what you expected to see.
      </p>

      <p className="mt-10 rounded-lg bg-slate-100 px-4 py-3 text-xs text-slate-500 dark:bg-slate-800/60 dark:text-slate-400">
        Market data is delayed and provided for educational purposes only.
        Nothing on this site is investment advice.
      </p>
    </div>
  );
}
