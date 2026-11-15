import { AlertTriangle, Brain, Check, Database, PenLine, ShieldX, Sparkles, Wrench, X } from "lucide-react";

const ICONS = {
  Planner: Brain,
  "SQL Writer": PenLine,
  Executor: Database,
  "SQL Fixer": Wrench,
  Analyst: Sparkles,
};

const STATUS = {
  ok: { icon: Check, ring: "border-tide bg-tide-soft text-tide", label: "done" },
  error: { icon: AlertTriangle, ring: "border-amber bg-amber-soft text-amber", label: "query failed" },
  blocked: { icon: ShieldX, ring: "border-rust bg-rust-soft text-rust", label: "blocked" },
  refused: { icon: X, ring: "border-rust bg-rust-soft text-rust", label: "declined" },
  failed: { icon: X, ring: "border-rust bg-rust-soft text-rust", label: "gave up" },
};

const PIPELINE = ["Planner", "SQL Writer", "Executor", "Analyst"];

/** Live placeholder while the agents work (the API returns once at the end). */
export function AgentPipelinePending() {
  return (
    <ol className="space-y-3" aria-label="Agents working">
      {PIPELINE.map((name, i) => {
        const Icon = ICONS[name];
        return (
          <li key={name} className="flex items-center gap-3">
            <span className="relative grid h-8 w-8 shrink-0 place-items-center overflow-hidden rounded-full border border-rule bg-wash text-slate">
              <Icon className="h-4 w-4" aria-hidden />
              <span className="sweep absolute inset-y-0 left-0 w-1/2 bg-gradient-to-r from-transparent via-white/80 to-transparent"
                style={{ animationDelay: `${i * 0.25}s` }} />
            </span>
            <span className="text-sm text-slate">{name}</span>
          </li>
        );
      })}
    </ol>
  );
}

export default function AgentTrace({ trace, attempts }) {
  if (!trace?.length) return null;
  const retries = Math.max(0, (attempts || 0) - 1);
  return (
    <div>
      {retries > 0 && (
        <p className="mb-3 rounded-lg bg-amber-soft px-3 py-2 text-sm text-ink">
          The first query failed; the Fixer corrected it {retries === 1 ? "once" : `${retries} times`}.
        </p>
      )}
      <ol className="relative space-y-4">
        <span className="absolute left-4 top-4 bottom-4 w-px bg-rule" aria-hidden />
        {trace.map((s, i) => {
          const Icon = ICONS[s.agent] || Sparkles;
          const st = STATUS[s.status] || STATUS.ok;
          return (
            <li key={i} className="appear relative flex gap-3" style={{ animationDelay: `${i * 60}ms` }}>
              <span className={`relative z-10 grid h-8 w-8 shrink-0 place-items-center rounded-full border ${st.ring}`}>
                <Icon className="h-4 w-4" aria-hidden />
              </span>
              <div className="min-w-0 flex-1 pt-0.5">
                <p className="flex flex-wrap items-baseline gap-x-2 text-sm">
                  <span className="font-semibold">{s.agent}</span>
                  <span className="text-slate">{st.label}</span>
                  <span className="tnum ml-auto text-xs text-slate">{(s.ms / 1000).toFixed(1)}s</span>
                </p>
                {s.detail && <p className="mt-0.5 text-sm text-ink-2">{s.detail}</p>}
                {s.tables && <p className="mt-0.5 text-xs text-slate">Tables: {s.tables}</p>}
                {s.sql && (
                  <pre className="mt-1.5 max-h-40 overflow-auto rounded-md bg-wash p-2 font-mono text-[12px] leading-relaxed text-ink-2">
                    {s.sql}
                  </pre>
                )}
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
