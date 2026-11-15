const MONEY_HINT = /(revenue|spend|sales|profit|price|cost|value|aov|amount|inr)/i;

export function formatCell(value, column = "") {
  if (value === null || value === undefined) return "–";
  if (typeof value === "number") {
    if (MONEY_HINT.test(column)) return "₹" + value.toLocaleString("en-IN", { maximumFractionDigits: 2 });
    if (/(pct|percent|rate|share|margin|growth)/i.test(column)) return `${value.toLocaleString("en-IN", { maximumFractionDigits: 1 })}%`;
    return value.toLocaleString("en-IN", { maximumFractionDigits: 2 });
  }
  return String(value);
}

export function compactNumber(v) {
  if (typeof v !== "number") return v;
  const a = Math.abs(v);
  if (a >= 1e7) return `${(v / 1e7).toFixed(1)}Cr`;
  if (a >= 1e5) return `${(v / 1e5).toFixed(1)}L`;
  if (a >= 1e3) return `${(v / 1e3).toFixed(1)}K`;
  return v.toLocaleString("en-IN", { maximumFractionDigits: 1 });
}

export const titleCase = (s = "") => s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
