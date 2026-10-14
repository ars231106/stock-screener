import Link from "next/link";

import SearchBar from "@/components/SearchBar";

const POPULAR = [
  "TCS",
  "Reliance",
  "Infosys",
  "HDFC Bank",
  "Tata Motors",
  "ITC",
  "Apple",
  "Microsoft",
  "Google",
  "Amazon",
  "Nvidia",
  "Meta",
  "Tesla",
  "Netflix",
  "AMD",
  "Johnson & Johnson",
];

const HIGHLIGHTS = [
  {
    title: "Fundamentals, not just prices",
    body: "P/E, P/B, margins, return on equity, revenue and earnings growth — pulled per company and cached so pages stay fast.",
  },
  {
    title: "Screens that actually run",
    body: "Growth, value, dividend and quality presets execute against a live universe. Build your own criteria and save them.",
  },
  {
    title: "A watchlist that persists",
    body: "Sign in once and your symbols follow you across devices, stored in Postgres rather than a browser tab.",
  },
];

export default function HomePage() {
  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
      <section className="pb-8 pt-16 text-center sm:pt-24">
        <h1 className="mx-auto max-w-3xl text-2xl font-semibold leading-snug text-slate-800 dark:text-slate-100 sm:text-3xl">
          Stock analysis and screening tool for investors around the world.
        </h1>

        <div className="mt-10">
          <SearchBar autoFocus />
        </div>

        <div className="mt-10">
          <p className="muted">Or analyse:</p>
          <div className="mx-auto mt-4 flex max-w-4xl flex-wrap justify-center gap-2">
            {POPULAR.map((name) => (
              <Link
                key={name}
                href={`/search?q=${encodeURIComponent(name)}`}
                className="tag"
              >
                {name}
              </Link>
            ))}
          </div>
        </div>
      </section>

      <section className="grid gap-5 py-12 md:grid-cols-3">
        {HIGHLIGHTS.map((item) => (
          <div key={item.title} className="card">
            <h2 className="text-base font-semibold text-slate-800 dark:text-slate-100">
              {item.title}
            </h2>
            <p className="muted mt-2">{item.body}</p>
          </div>
        ))}
      </section>

      <section className="card mb-12 flex flex-col items-start justify-between gap-4 bg-gradient-to-r from-brand/5 to-brand-light/10 sm:flex-row sm:items-center dark:from-brand/10 dark:to-brand-light/10">
        <div>
          <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100">
            Start with a ready-made screen
          </h2>
          <p className="muted mt-1">
            Four presets are built in — growth, value, dividend and quality
            compounders.
          </p>
        </div>
        <Link href="/screens" className="btn-primary shrink-0">
          Browse screens
        </Link>
      </section>
    </div>
  );
}
