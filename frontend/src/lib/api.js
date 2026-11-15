const BASE = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");

async function request(path, options = {}) {
  let res;
  try {
    res = await fetch(`${BASE}${path}`, {
      ...options,
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    });
  } catch {
    throw new Error("Can't reach the backend. Start it with: uvicorn app.main:app --port 8000");
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const d = data.detail;
    throw new Error(Array.isArray(d) ? d.map((x) => x.msg).join(", ") : d || `Request failed (${res.status})`);
  }
  return data;
}

export const api = {
  health: () => request("/api/health"),
  schema: () => request("/api/schema"),
  examples: () => request("/api/examples"),
  ask: (question) => request("/api/ask", { method: "POST", body: JSON.stringify({ question }) }),
  runSql: (sql) => request("/api/sql", { method: "POST", body: JSON.stringify({ sql }) }),
};
