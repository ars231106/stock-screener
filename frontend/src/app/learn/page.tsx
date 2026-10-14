import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Learn",
  description: "What each metric in the screener actually measures.",
};

const GLOSSARY = [
  {
    term: "P/E ratio",
    body: "Price divided by earnings per share. Roughly, what you pay for one rupee of annual profit. Low can mean cheap or it can mean the market expects profits to fall.",
  },
  {
    term: "P/B ratio",
    body: "Price divided by book value per share. Most useful for banks and asset-heavy businesses, where book value tracks something real.",
  },
  {
    term: "PEG ratio",
    body: "P/E divided by the earnings growth rate. An attempt to compare valuation across companies growing at different speeds.",
  },
  {
    term: "Return on equity (ROE)",
    body: "Net profit as a share of shareholders' equity. High and steady ROE usually signals a business with some durable advantage — or a lot of leverage.",
  },
  {
    term: "Operating margin",
    body: "Operating profit as a share of revenue. Shows how much of each sale survives the cost of running the business, before financing and tax.",
  },
  {
    term: "Dividend yield",
    body: "Annual dividend divided by price. A very high yield is often a falling price rather than a generous payout.",
  },
  {
    term: "Beta",
    body: "How much the stock has moved relative to the wider market. Above 1 means it has historically swung harder than the index in both directions.",
  },
];

export default function LearnPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-16 sm:px-6">
      <h1 className="section-title">Learn</h1>
      <p className="muted mt-4">
        What each metric in the screener measures, and where it misleads.
      </p>

      <dl className="mt-10 space-y-6">
        {GLOSSARY.map((item) => (
          <div key={item.term} className="card">
            <dt className="font-semibold text-slate-900 dark:text-slate-100">
              {item.term}
            </dt>
            <dd className="muted mt-2 leading-relaxed">{item.body}</dd>
          </div>
        ))}
      </dl>

      <p className="mt-10">
        <Link href="/screens" className="btn-primary inline-flex">
          Try a screen
        </Link>
      </p>
    </div>
  );
}
