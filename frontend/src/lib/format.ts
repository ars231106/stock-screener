const CURRENCY_SYMBOLS: Record<string, string> = {
  USD: "$",
  INR: "₹",
  EUR: "€",
  GBP: "£",
  JPY: "¥",
  CAD: "C$",
  AUD: "A$",
  HKD: "HK$",
  SGD: "S$",
  KRW: "₩",
  BRL: "R$",
};

export function currencySymbol(code?: string | null): string {
  if (!code) return "";
  return CURRENCY_SYMBOLS[code.toUpperCase()] ?? `${code.toUpperCase()} `;
}

export function money(value?: number | null, symbol = ""): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `${symbol}${value.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

export function compact(value?: number | null): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const abs = Math.abs(value);
  if (abs >= 1e12) return `${(value / 1e12).toFixed(2)}T`;
  if (abs >= 1e9) return `${(value / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `${(value / 1e6).toFixed(2)}M`;
  if (abs >= 1e3) return `${(value / 1e3).toFixed(2)}K`;
  return value.toFixed(2);
}

/** Alpha Vantage returns ratios as decimals (0.153 = 15.3%). */
export function percent(value?: number | null, decimals = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `${(value * 100).toFixed(decimals)}%`;
}

export function ratio(value?: number | null): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return value.toFixed(2);
}

export function volume(value?: number | null): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return value.toLocaleString();
}

/** Formats a metric using the unit hint the API gives us. */
export function metricValue(
  value: number | null | undefined,
  unit: string
): string {
  if (value === null || value === undefined) return "—";
  if (unit === "pct") return percent(value);
  if (unit === "abs") return compact(value);
  if (unit === "x") return `${value.toFixed(2)}x`;
  return ratio(value);
}

export function changeTone(change?: number | null): "up" | "down" | "flat" {
  if (change === null || change === undefined || Number.isNaN(change))
    return "flat";
  if (change > 0) return "up";
  if (change < 0) return "down";
  return "flat";
}

export function timeAgo(iso?: string | null): string {
  if (!iso) return "";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "";
  const seconds = Math.floor((Date.now() - then) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}
