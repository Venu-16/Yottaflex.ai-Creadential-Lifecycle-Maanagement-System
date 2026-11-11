import { RefreshCw, Search } from "lucide-react";

export function PageHeader({ eyebrow, title, description, action }) {
  return (
    <div className="mb-7 flex flex-wrap items-end justify-between gap-4">
      <div>
        {eyebrow && <p className="mb-2 text-xs font-bold uppercase tracking-[0.16em] text-sage-700">{eyebrow}</p>}
        <h1 className="text-3xl font-semibold tracking-tight text-ink">{title}</h1>
        {description && <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">{description}</p>}
      </div>
      {action}
    </div>
  );
}

export function Card({ children, className = "" }) {
  return <section className={`rounded-2xl border border-line bg-white p-5 shadow-card ${className}`}>{children}</section>;
}

export function Button({ children, variant = "primary", className = "", ...props }) {
  const styles = variant === "danger"
    ? "bg-rose-700 text-white hover:bg-rose-800"
    : variant === "secondary"
      ? "border border-line bg-white text-ink hover:bg-stone-50"
      : "bg-sage-800 text-white hover:bg-sage-900";
  return <button className={`inline-flex min-h-10 items-center justify-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-50 ${styles} ${className}`} {...props}>{children}</button>;
}

export function Field({ label, className = "", inputClassName = "", as, type = "text", ...props }) {
  const controlClass = `w-full rounded-xl border border-line bg-ivory px-3 py-2.5 text-sm outline-none transition focus:border-sage-600 focus:ring-2 focus:ring-sage-100 ${inputClassName}`;
  return (
    <label className={`block text-sm font-medium text-ink ${className}`}>
      <span className="mb-1.5 block">{label}</span>
      {as === "textarea" ? (
        <textarea {...props} className={controlClass} />
      ) : (
        <input {...props} type={type} className={controlClass} />
      )}
    </label>
  );
}

export function SelectField({ label, children, className = "", ...props }) {
  return (
    <label className={`block text-sm font-medium text-ink ${className}`}>
      <span className="mb-1.5 block">{label}</span>
      <select {...props} className="w-full rounded-xl border border-line bg-ivory px-3 py-2.5 text-sm outline-none focus:border-sage-600 focus:ring-2 focus:ring-sage-100">{children}</select>
    </label>
  );
}

export function Notice({ children, tone = "error" }) {
  const styles = tone === "success" ? "border-sage-200 bg-sage-50 text-sage-900" : "border-rose-200 bg-rose-50 text-rose-800";
  return <div role={tone === "error" ? "alert" : "status"} className={`rounded-xl border px-4 py-3 text-sm ${styles}`}>{children}</div>;
}

export function SearchBox({ value, onChange, placeholder = "Search this page" }) {
  return (
    <label className="relative block w-full sm:max-w-xs">
      <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
      <input value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} className="w-full rounded-xl border border-line bg-white py-2.5 pl-9 pr-3 text-sm outline-none focus:border-sage-600 focus:ring-2 focus:ring-sage-100" />
    </label>
  );
}

export function DataTable({ columns, rows, empty = "No records found." }) {
  if (!rows.length) return <div className="rounded-xl bg-ivory px-5 py-10 text-center text-sm text-muted">{empty}</div>;
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[640px] text-left text-sm">
        <thead><tr className="border-b border-line text-xs uppercase tracking-wide text-muted">{columns.map((column) => <th key={column.key} className="px-3 py-3 font-semibold">{column.label}</th>)}</tr></thead>
        <tbody className="divide-y divide-line">
          {rows.map((row, index) => <tr key={row.id || row.credential_id || row.verification_id || index} className="align-top hover:bg-ivory/70">
            {columns.map((column) => <td key={column.key} className="max-w-[360px] px-3 py-3 text-ink">{column.render ? column.render(row) : (row[column.key] ?? "—")}</td>)}
          </tr>)}
        </tbody>
      </table>
    </div>
  );
}

export function LoadingState({ label = "Loading records…" }) {
  return <div className="flex items-center gap-2 py-8 text-sm text-muted"><RefreshCw size={16} className="animate-spin" />{label}</div>;
}

export function StatusPill({ value }) {
  const positive = ["active", "completed", "eligible", "valid", "trusted"].includes(String(value).toLowerCase());
  const negative = ["revoked", "ineligible", "tampered", "invalid_signature"].includes(String(value).toLowerCase());
  return <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${positive ? "bg-sage-100 text-sage-900" : negative ? "bg-rose-100 text-rose-800" : "bg-lavender-100 text-lavender-800"}`}>{String(value || "unknown").replaceAll("_", " ")}</span>;
}
