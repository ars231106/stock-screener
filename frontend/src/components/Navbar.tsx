"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";

import { useAuth } from "./AuthProvider";
import { useTheme } from "./ThemeProvider";

const NAV = [
  { href: "/", label: "Home" },
  { href: "/screens", label: "Screens" },
  { href: "/tools", label: "Tools" },
  { href: "/watchlist", label: "Watchlist" },
];

function Logo() {
  return (
    <Link href="/" className="flex items-end gap-[3px] text-2xl font-semibold">
      <span className="text-slate-800 dark:text-slate-100">screener</span>
      <span className="text-ticker-up">.in</span>
      <span className="ml-1 flex items-end gap-[3px] pb-1">
        <span className="h-3 w-2 rounded-full bg-ticker-up" />
        <span className="h-[18px] w-2 rounded-full bg-ticker-up" />
        <span className="h-6 w-2 rounded-full bg-ticker-up" />
      </span>
    </Link>
  );
}

export default function Navbar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, loading, signOut } = useAuth();
  const { theme, toggle } = useTheme();
  const [menuOpen, setMenuOpen] = useState(false);

  const displayName =
    (user?.user_metadata?.username as string | undefined) ||
    user?.email?.split("@")[0];

  async function handleSignOut() {
    await signOut();
    router.push("/");
  }

  return (
    <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/90 backdrop-blur dark:border-slate-800 dark:bg-surface-dark/90">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-4 py-3 sm:px-6 lg:px-8">
        <Logo />

        <nav className="order-3 w-full sm:order-2 sm:w-auto">
          <ul className="flex flex-wrap items-center gap-1 sm:gap-2">
            {NAV.map((item) => {
              const active =
                item.href === "/"
                  ? pathname === "/"
                  : pathname.startsWith(item.href);
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    className={`rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                      active
                        ? "bg-brand/10 text-brand dark:bg-brand/20 dark:text-brand-light"
                        : "text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-white"
                    }`}
                  >
                    {item.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>

        <div className="order-2 flex items-center gap-2 sm:order-3">
          <button
            type="button"
            onClick={toggle}
            aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-600 transition hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            {theme === "dark" ? "☀" : "☾"}
          </button>

          {loading ? (
            <div className="h-9 w-24 animate-pulse rounded-md bg-slate-200 dark:bg-slate-800" />
          ) : user ? (
            <div className="relative">
              <button
                type="button"
                onClick={() => setMenuOpen((o) => !o)}
                className="rounded-md border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
              >
                Hi, {displayName} ▾
              </button>
              {menuOpen && (
                <div
                  className="absolute right-0 mt-2 w-44 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-lg dark:border-slate-700 dark:bg-surface-dark"
                  onMouseLeave={() => setMenuOpen(false)}
                >
                  <Link
                    href="/watchlist"
                    onClick={() => setMenuOpen(false)}
                    className="block px-4 py-2 text-sm text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800"
                  >
                    My watchlist
                  </Link>
                  <Link
                    href="/history"
                    onClick={() => setMenuOpen(false)}
                    className="block px-4 py-2 text-sm text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800"
                  >
                    Search history
                  </Link>
                  <button
                    type="button"
                    onClick={handleSignOut}
                    className="block w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-slate-100 dark:hover:bg-slate-800"
                  >
                    Log out
                  </button>
                </div>
              )}
            </div>
          ) : (
            <>
              <Link
                href="/login"
                className="rounded-md border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
              >
                Login
              </Link>
              <Link
                href="/login?mode=signup"
                className="rounded-md bg-brand-light px-3 py-2 text-sm font-semibold text-white transition hover:bg-brand"
              >
                Get New Account
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
