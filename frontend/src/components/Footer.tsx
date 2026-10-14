"use client";

import Link from "next/link";

import { useTheme } from "./ThemeProvider";

export default function Footer() {
  const { theme, setTheme } = useTheme();

  return (
    <footer className="mt-16 border-t border-slate-200 bg-white dark:border-slate-800 dark:bg-surface-dark">
      <div className="mx-auto grid max-w-7xl gap-8 px-4 py-10 sm:px-6 md:grid-cols-2 lg:px-8">
        <div>
          <div className="text-xl font-semibold text-slate-800 dark:text-slate-100">
            screener<span className="text-ticker-up">.in</span>
          </div>
          <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
            Stock analysis and screening tool.
          </p>
          <p className="text-sm text-slate-500 dark:text-slate-400">Made in India.</p>
          <p className="mt-4 max-w-md text-xs text-slate-400 dark:text-slate-500">
            Market data is delayed and provided for educational purposes only.
            Nothing here is investment advice.
          </p>
        </div>

        <div className="grid grid-cols-2 gap-8 sm:grid-cols-3">
          <div>
            <h4 className="text-sm font-semibold text-slate-800 dark:text-slate-100">
              Product
            </h4>
            <ul className="mt-3 space-y-2 text-sm text-slate-500 dark:text-slate-400">
              <li>
                <Link href="/screens" className="hover:text-brand">
                  Screens
                </Link>
              </li>
              <li>
                <Link href="/tools" className="hover:text-brand">
                  Tools
                </Link>
              </li>
              <li>
                <Link href="/learn" className="hover:text-brand">
                  Learn
                </Link>
              </li>
            </ul>
          </div>

          <div>
            <h4 className="text-sm font-semibold text-slate-800 dark:text-slate-100">
              Team
            </h4>
            <ul className="mt-3 space-y-2 text-sm text-slate-500 dark:text-slate-400">
              <li>
                <Link href="/about" className="hover:text-brand">
                  About us
                </Link>
              </li>
              <li>
                <Link href="/about#support" className="hover:text-brand">
                  Support
                </Link>
              </li>
            </ul>
          </div>

          <div>
            <h4 className="text-sm font-semibold text-slate-800 dark:text-slate-100">
              Theme
            </h4>
            <ul className="mt-3 space-y-2 text-sm">
              <li>
                <button
                  type="button"
                  onClick={() => setTheme("light")}
                  className={
                    theme === "light"
                      ? "font-semibold text-brand"
                      : "text-slate-500 hover:text-brand dark:text-slate-400"
                  }
                >
                  Light
                </button>
              </li>
              <li>
                <button
                  type="button"
                  onClick={() => setTheme("dark")}
                  className={
                    theme === "dark"
                      ? "font-semibold text-brand-light"
                      : "text-slate-500 hover:text-brand dark:text-slate-400"
                  }
                >
                  Dark
                </button>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </footer>
  );
}
