import { KeyRound, Link2, X } from "lucide-react";

export default function SchemaPanel({ schema, onClose }) {
  return (
    <div className="fixed inset-0 z-40" role="dialog" aria-modal="true" aria-label="Database schema">
      <div className="absolute inset-0 bg-ink/40" onClick={onClose} />
      <aside className="absolute inset-y-0 right-0 flex w-full max-w-md flex-col bg-card shadow-xl">
        <div className="flex items-center justify-between border-b border-rule px-5 py-4">
          <div>
            <h2 className="text-lg font-semibold">What's in the database</h2>
            <p className="text-sm text-slate">ShopKart, a demo Indian online store, 2024–2025</p>
          </div>
          <button onClick={onClose} className="rounded-md p-2 text-slate hover:bg-wash" aria-label="Close"><X className="h-5 w-5" /></button>
        </div>
        <div className="flex-1 space-y-4 overflow-auto p-5">
          {!schema && <p className="text-slate">Loading…</p>}
          {schema?.tables.map((t) => (
            <section key={t.name} className="card p-4">
              <h3 className="flex items-baseline justify-between font-mono text-sm font-medium">
                {t.name}<span className="tnum font-sans text-xs text-slate">{t.row_count.toLocaleString("en-IN")} rows</span>
              </h3>
              <ul className="mt-2 space-y-1.5 text-sm">
                {t.columns.map((c) => (
                  <li key={c.name}>
                    <span className="inline-flex items-center gap-1.5 font-mono text-[13px]">
                      {c.pk && <KeyRound className="h-3.5 w-3.5 text-amber" aria-label="primary key" />}
                      {c.fk && <Link2 className="h-3.5 w-3.5 text-tide" aria-label={`links to ${c.fk}`} />}
                      {c.name}
                    </span>
                    <span className="ml-2 text-xs text-slate">{c.type.toLowerCase()}</span>
                    {c.values && <p className="text-xs text-slate">{c.values.join(", ")}</p>}
                    {c.range && <p className="text-xs text-slate">{c.range[0]} to {c.range[1]}</p>}
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      </aside>
    </div>
  );
}
