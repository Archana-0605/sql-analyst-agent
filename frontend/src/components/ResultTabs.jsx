import { useEffect, useState } from "react";
import { Copy, Download, Play } from "lucide-react";
import { api } from "../lib/api";
import { formatCell, titleCase } from "../lib/format";
import ResultChart from "./ResultChart";

function toCsv(columns, rows) {
  const esc = (v) => (v === null || v === undefined ? "" : /[",\n]/.test(String(v)) ? `"${String(v).replace(/"/g, '""')}"` : String(v));
  return [columns.map(esc).join(","), ...rows.map((r) => r.map(esc).join(","))].join("\n");
}

function DataTable({ columns, rows }) {
  return (
    <div className="max-h-[420px] overflow-auto rounded-lg border border-rule">
      <table className="w-full text-sm">
        <thead className="sticky top-0 bg-wash text-left">
          <tr>{columns.map((c) => <th key={c} className="whitespace-nowrap px-3 py-2 font-semibold text-ink-2">{titleCase(c)}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className="border-t border-rule/70">
              {r.map((v, j) => (
                <td key={j} className={`whitespace-nowrap px-3 py-2 ${typeof v === "number" ? "tnum text-right" : ""}`}>
                  {formatCell(v, columns[j])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function ResultTabs({ result, onResult }) {
  const hasChart = result.chart?.type && result.chart.type !== "none";
  const [tab, setTab] = useState(hasChart ? "chart" : "table");
  const [sql, setSql] = useState(result.sql || "");
  const [runState, setRunState] = useState({ busy: false, error: "" });

  useEffect(() => {
    setTab(result.chart?.type && result.chart.type !== "none" ? "chart" : "table");
    setSql(result.sql || "");
    setRunState({ busy: false, error: "" });
  }, [result]);

  const run = async () => {
    setRunState({ busy: true, error: "" });
    try {
      const r = await api.runSql(sql);
      onResult({ ...result, ...r, sql: r.sql, edited: true });
      setTab(r.chart?.type !== "none" ? "chart" : "table");
    } catch (e) {
      setRunState({ busy: false, error: e.message });
      return;
    }
    setRunState({ busy: false, error: "" });
  };

  const download = () => {
    const blob = new Blob([toCsv(result.columns, result.rows)], { type: "text/csv" });
    const a = Object.assign(document.createElement("a"), { href: URL.createObjectURL(blob), download: "result.csv" });
    a.click();
    URL.revokeObjectURL(a.href);
  };

  const tabs = [hasChart && ["chart", "Chart"], ["table", `Table (${result.row_count})`], ["sql", "SQL"]].filter(Boolean);

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <div className="inline-flex rounded-lg bg-wash p-1" role="tablist">
          {tabs.map(([key, label]) => (
            <button key={key} role="tab" aria-selected={tab === key} onClick={() => setTab(key)}
              className={`rounded-md px-3 py-1.5 text-sm font-semibold transition ${tab === key ? "bg-card text-ink shadow-sm" : "text-slate hover:text-ink"}`}>
              {label}
            </button>
          ))}
        </div>
        {result.row_count > 0 && (
          <button onClick={download} className="btn-line ml-auto"><Download className="h-4 w-4" aria-hidden /> Download CSV</button>
        )}
      </div>

      {tab === "chart" && <ResultChart chart={result.chart} columns={result.columns} rows={result.rows} />}
      {tab === "table" && (result.row_count ? <DataTable columns={result.columns} rows={result.rows} />
        : <p className="py-8 text-center text-slate">No rows returned.</p>)}
      {tab === "sql" && (
        <div>
          <label htmlFor="sql" className="sr-only">SQL query</label>
          <textarea id="sql" value={sql} onChange={(e) => setSql(e.target.value)} spellCheck={false} rows={Math.min(16, sql.split("\n").length + 2)}
            className="w-full resize-y rounded-lg border border-rule bg-wash p-3 font-mono text-[13px] leading-relaxed text-ink outline-none focus:border-tide" />
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <button onClick={run} disabled={runState.busy || !sql.trim()} className="btn-ink">
              <Play className="h-4 w-4" aria-hidden /> {runState.busy ? "Running…" : "Run edited query"}
            </button>
            <button onClick={() => navigator.clipboard?.writeText(sql)} className="btn-line"><Copy className="h-4 w-4" aria-hidden /> Copy</button>
            <span className="text-xs text-slate">Read-only: the same safety checks as the agents apply.</span>
          </div>
          {runState.error && <p className="mt-2 rounded-lg bg-rust-soft px-3 py-2 text-sm text-rust" role="alert">{runState.error}</p>}
        </div>
      )}
    </div>
  );
}
