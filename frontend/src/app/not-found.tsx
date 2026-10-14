import Link from "next/link";

export default function NotFound() {
  return (
    <div className="mx-auto max-w-xl px-4 py-24 text-center">
      <p className="text-5xl font-semibold text-brand">404</p>
      <h1 className="section-title mt-4">Page not found</h1>
      <p className="muted mt-3">
        That page does not exist. Try searching for a company instead.
      </p>
      <Link href="/" className="btn-primary mt-8 inline-flex">
        Back home
      </Link>
    </div>
  );
}
