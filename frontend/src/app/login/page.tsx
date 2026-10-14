"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { useAuth } from "@/components/AuthProvider";

function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const { user, signIn, signUp, configured } = useAuth();

  const [isSignup, setIsSignup] = useState(params.get("mode") === "signup");
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    if (user) router.replace("/watchlist");
  }, [user, router]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setNotice(null);

    if (!email.trim() || !password) {
      setError("Fill in both fields.");
      return;
    }
    if (isSignup && password.length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }

    setBusy(true);
    try {
      if (isSignup) {
        const { needsConfirmation } = await signUp(
          email.trim(),
          password,
          username.trim() || undefined
        );
        if (needsConfirmation) {
          setNotice(
            "Check your inbox for a confirmation link, then come back and log in."
          );
          setIsSignup(false);
        } else {
          router.push("/watchlist");
        }
      } else {
        await signIn(email.trim(), password);
        router.push("/watchlist");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  if (!configured) {
    return (
      <div className="card mx-auto mt-20 max-w-md">
        <h1 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
          Authentication is not configured
        </h1>
        <p className="muted mt-2">
          Set <code>NEXT_PUBLIC_SUPABASE_URL</code> and{" "}
          <code>NEXT_PUBLIC_SUPABASE_ANON_KEY</code> in your environment, then
          redeploy.
        </p>
      </div>
    );
  }

  return (
    <div className="card mx-auto mt-16 mb-20 max-w-md">
      <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-100">
        {isSignup ? "Create your account" : "Log in"}
      </h1>
      <p className="muted mt-1">
        {isSignup
          ? "Your watchlist and saved screens are tied to this account."
          : "Welcome back."}
      </p>

      <form onSubmit={onSubmit} className="mt-6 space-y-4">
        <div>
          <label className="label" htmlFor="email">
            Email
          </label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            className="input"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>

        {isSignup && (
          <div>
            <label className="label" htmlFor="username">
              Username (optional)
            </label>
            <input
              id="username"
              type="text"
              className="input"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </div>
        )}

        <div>
          <label className="label" htmlFor="password">
            Password
          </label>
          <input
            id="password"
            type="password"
            autoComplete={isSignup ? "new-password" : "current-password"}
            className="input"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>

        {error && (
          <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950/40 dark:text-red-300">
            {error}
          </p>
        )}
        {notice && (
          <p className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300">
            {notice}
          </p>
        )}

        <button type="submit" disabled={busy} className="btn-primary w-full">
          {busy ? "Please wait…" : isSignup ? "Create account" : "Log in"}
        </button>
      </form>

      <p className="muted mt-6 text-center">
        {isSignup ? "Already have an account?" : "Don't have an account?"}{" "}
        <button
          type="button"
          onClick={() => {
            setIsSignup((s) => !s);
            setError(null);
            setNotice(null);
          }}
          className="font-semibold text-brand hover:underline"
        >
          {isSignup ? "Log in" : "Sign up"}
        </button>
      </p>

      <p className="muted mt-4 text-center text-xs">
        <Link href="/" className="hover:underline">
          ← Back home
        </Link>
      </p>
    </div>
  );
}

export default function LoginPage() {
  return (
    <div className="px-4">
      <Suspense fallback={<p className="muted mt-20 text-center">Loading…</p>}>
        <LoginForm />
      </Suspense>
    </div>
  );
}
