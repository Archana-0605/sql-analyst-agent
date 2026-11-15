import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { ArrowUp, Clock, Database, History } from "lucide-react";
import { api } from "./lib/api";
import AgentTrace, { AgentPipelinePending } from "./components/AgentTrace";
import ResultTabs from "./components/ResultTabs";
import SchemaPanel from "./components/SchemaPanel";

const STORE = "analyst-desk-history";

function loadHistory() {
  try { return JSON.parse(localStorage.getItem(STORE)) || []; } catch { return []; }
}

function Logo() {
  return (
    <div className="flex items-center gap-2.5">
      <svg viewBox="0 0 32 32" className="h-8 w-8" aria-hidden>
        <rect width="32" height="32" rx="7" fill="#16224a" />
        <rect x="7" y="17" width="4" height="8" rx="1" fill="#5cc8c0" />
        <rect x="14" y="12" width="4" height="13" rx="1" fill="#5cc8c0" />
        <rect x="21" y="7" width="4" height="18" rx="1" fill="#f2b84b" />
      </svg>
      <span className="text-[17px] font-semibold">Analyst Desk</span>
    </div>
  );
}

export default function App() {
  const [health, setHealth] = useState(null);
  const [examples, setExamples] = useState([]);
  const [schema, setSchema] = useState(null);
  const [showSchema, setShowSchema] = useState(false);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState(loadHistory);
  const inputRef = useRef(null);

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth({ offline: true }));
    api.examples().then((d) => setExamples(d.examples)).catch(() => {});
    api.schema().then(setSchema).catch(() => {});
  }, []);

  useEffect(() => {
    try { localStorage.setItem(STORE, JSON.stringify(history.slice(0, 12))); } catch { /* storage blocked */ }
  }, [history]);

  const ask = async (q = question) => {
    const text = q.trim();
    if (!text || busy) return;
    setQuestion(text);
    setBusy(true);
    setError("");
    setResult(null);
    try {
      const r = await api.ask(text);
      setResult(r);
      setHistory((h) => [{ question: text, status: r.status, at: Date.now() }, ...h.filter((x) => x.question !== text)]);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const status = health?.offline
    ? { dot: "bg-rust", text: "Backend offline" }
    : health && !health.llm_configured
      ? { dot: "bg-amber", text: "Add a Groq API key to backend/.env" }
      : health ? { dot: "bg-tide", text: health.model } : { dot: "bg-rule", text: "Connecting…" };

  return (
    <div className="min-h-screen">
      <header className="border-b border-rule bg-card">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
          <Logo />
          <div className="flex items-center gap-3">
            <span className="hidden items-center gap-2 text-sm text-slate sm:inline-flex">
              <span className={`h-2 w-2 rounded-full ${status.dot}`} aria-hidden />{status.text}
            </span>
            <button onClick={() => setShowSchema(true)} className="btn-line"><Database className="h-4 w-4" aria-hidden /> Data</button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-10">
        <section className="max-w-3xl">
          <h1 className="text-3xl font-bold sm:text-4xl">Ask your sales data anything.</h1>
          <p className="mt-2 text-[17px] text-slate">
            Four AI agents plan the analysis, write the SQL, fix it if it fails, and explain the answer,
            all on a read-only copy of the store's database.
          </p>

          <form onSubmit={(e) => { e.preventDefault(); ask(); }}
            className="mt-6 flex items-end gap-2 rounded-xl border border-rule bg-card p-2 shadow-[0_6px_24px_-12px_rgba(22,34,74,0.35)] focus-within:border-tide">
            <label htmlFor="q" className="sr-only">Your question</label>
            <textarea id="q" ref={inputRef} rows={1} value={question} maxLength={500}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); ask(); } }}
              placeholder="e.g. Which category made the most profit last year?"
              className="max-h-32 min-w-0 flex-1 resize-none bg-transparent px-3 py-2.5 text-[16px] outline-none focus-visible:outline-none" />
            <button className="btn-ink h-11 w-11 p-0" disabled={busy || question.trim().length < 3} aria-label="Ask">
              <ArrowUp className="h-5 w-5" />
            </button>
          </form>

          {examples.length > 0 && (
            <ul className="mt-3 flex flex-wrap gap-2" aria-label="Example questions">
              {examples.map((ex) => (
                <li key={ex}>
                  <button onClick={() => ask(ex)} disabled={busy}
                    className="rounded-full border border-rule bg-card px-3 py-1.5 text-sm text-ink-2 transition hover:border-tide hover:text-ink">
                    {ex}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        {error && <p className="mt-8 max-w-3xl rounded-xl border border-rust/30 bg-rust-soft px-4 py-3 text-rust" role="alert">{error}</p>}

        {(busy || result) && (
          <section className="mt-10 grid grid-cols-[minmax(0,1fr)] gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
            <div className="card min-w-0 p-5 sm:p-6">
              {busy && (
                <div aria-live="polite">
                  <p className="text-sm text-slate">Working on</p>
                  <p className="mt-1 text-lg font-semibold">{question}</p>
                  <div className="mt-5 space-y-2.5" aria-hidden>
                    <div className="h-3 w-3/4 rounded bg-wash" /><div className="h-3 w-2/3 rounded bg-wash" /><div className="h-40 rounded-lg bg-wash" />
                  </div>
                </div>
              )}
              {result && (
                <div className="appear">
                  <p className="text-sm text-slate">{result.edited ? "Edited query" : "Question"}</p>
                  <h2 className="mt-1 text-xl font-semibold">{result.question}</h2>
                  {!result.edited && (
                    <div className={`answer mt-4 rounded-lg px-4 py-3 text-[16px] leading-relaxed ${result.status === "answered" ? "bg-tide-soft/60" : "bg-amber-soft"}`}>
                      <ReactMarkdown>{result.answer}</ReactMarkdown>
                    </div>
                  )}
                  {result.status === "answered" && (
                    <div className="mt-6"><ResultTabs result={result} onResult={setResult} /></div>
                  )}
                </div>
              )}
            </div>

            <aside className="card h-fit min-w-0 p-5">
              <h2 className="mb-4 flex items-center justify-between font-semibold">
                How the agents worked
                {result && !busy && (
                  <span className="tnum inline-flex items-center gap-1 text-xs font-normal text-slate">
                    <Clock className="h-3.5 w-3.5" aria-hidden />{(result.latency_ms / 1000).toFixed(1)}s
                  </span>
                )}
              </h2>
              {busy ? <AgentPipelinePending /> : <AgentTrace trace={result?.trace} attempts={result?.attempts} />}
              {result?.tokens > 0 && !busy && <p className="mt-4 border-t border-rule pt-3 text-xs text-slate">{result.tokens.toLocaleString("en-IN")} tokens on {result.model}</p>}
            </aside>
          </section>
        )}

        {!busy && !result && history.length > 0 && (
          <section className="mt-12 max-w-3xl">
            <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate"><History className="h-4 w-4" aria-hidden /> Recent questions</h2>
            <ul className="divide-y divide-rule rounded-xl border border-rule bg-card">
              {history.slice(0, 6).map((h) => (
                <li key={h.question}>
                  <button onClick={() => ask(h.question)} className="w-full px-4 py-3 text-left text-[15px] hover:bg-wash">{h.question}</button>
                </li>
              ))}
            </ul>
          </section>
        )}
      </main>

      {showSchema && <SchemaPanel schema={schema} onClose={() => setShowSchema(false)} />}
    </div>
  );
}
