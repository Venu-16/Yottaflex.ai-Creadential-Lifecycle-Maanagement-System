import { useEffect, useState } from "react";
import {
  Activity, BadgeCheck, BarChart3, BookOpen, Clock3, Database,
  RefreshCw, ShieldCheck, Users,
} from "lucide-react";
import {
  Button, Card, DataTable, Field, LoadingState, Notice, PageHeader, SelectField, StatusPill,
} from "../../components/common/ui.jsx";
import api, { getErrorMessage } from "../../services/api.js";

const initialFilters = {
  date_from: "",
  date_to: "",
  course_id: "",
  credential_status: "",
  outcome: "",
};

function formatNumber(value) {
  return Number(value || 0).toLocaleString();
}

function formatRate(rate) {
  if (!rate || rate.percent === null) return "Not available";
  return `${rate.percent.toFixed(1)}%`;
}

function MetricCard({ label, value, detail, icon: Icon, tone = "sage" }) {
  const toneClass = tone === "lavender"
    ? "bg-lavender-100 text-lavender-900"
    : tone === "sand"
      ? "bg-amber-50 text-amber-800"
      : "bg-sage-100 text-sage-900";
  return (
    <Card className="flex min-w-0 items-start justify-between gap-3">
      <div className="min-w-0">
        <p className="text-sm text-muted">{label}</p>
        <p className="mt-3 break-words text-2xl font-semibold tracking-tight text-ink sm:text-3xl">{value}</p>
        {detail && <p className="mt-2 text-xs leading-5 text-muted">{detail}</p>}
      </div>
      <span className={`grid size-10 shrink-0 place-items-center rounded-xl ${toneClass}`}><Icon size={19} /></span>
    </Card>
  );
}

function BarList({ title, rows, labelKey = "key", empty = "No records match the selected filters." }) {
  const max = Math.max(0, ...rows.map((row) => row.count));
  return (
    <Card>
      <h2 className="font-semibold text-ink">{title}</h2>
      {!rows.length ? <p className="mt-4 rounded-xl bg-ivory px-4 py-6 text-center text-sm text-muted">{empty}</p> : (
        <div className="mt-4 space-y-3">
          {rows.map((row, index) => {
            const label = row[labelKey] || "Unspecified";
            const width = max > 0 ? Math.max(2, (row.count / max) * 100) : 0;
            return (
              <div key={`${label}-${index}`}>
                <div className="mb-1.5 flex items-center justify-between gap-3 text-xs">
                  <span className="min-w-0 truncate font-medium text-ink">{label}</span>
                  <span className="shrink-0 tabular-nums text-muted">{formatNumber(row.count)}</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-stone-100">
                  <div className="h-full rounded-full bg-sage-600" style={{ width: `${width}%` }} />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
}

function RateCard({ label, rate, icon }) {
  const definition = rate?.definition || "No rate definition is available.";
  return (
    <MetricCard
      label={label}
      value={formatRate(rate)}
      detail={rate ? `${formatNumber(rate.numerator)} / ${formatNumber(rate.denominator)} · ${definition}` : definition}
      icon={icon}
      tone="lavender"
    />
  );
}

function DataQuality({ report, error }) {
  if (error) return <Notice>{error}</Notice>;
  if (!report || report.status === "not_configured") {
    return <Notice>Dataset import and validation reports are not configured for this API instance.</Notice>;
  }
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <StatusPill value={report.status} />
        <span className="text-sm text-muted">Seed {report.seed ?? "—"} · {formatNumber(report.total_imported_rows)} imported of {formatNumber(report.total_expected_rows)} expected</span>
      </div>
      <dl className="grid gap-3 rounded-xl bg-ivory p-4 text-sm sm:grid-cols-3">
        <div><dt className="text-xs text-muted">Dataset SHA-256</dt><dd className="mt-1 break-all font-mono text-xs text-ink">{report.dataset_sha256 || "—"}</dd></div>
        <div><dt className="text-xs text-muted">Missing references</dt><dd className="mt-1 font-semibold text-ink">{formatNumber(report.missing_reference_count)}</dd></div>
        <div><dt className="text-xs text-muted">Last successful full validation</dt><dd className="mt-1 font-medium text-ink">{report.last_successful_validation_at ? new Date(report.last_successful_validation_at).toLocaleString() : "No successful validation recorded"}</dd></div>
      </dl>
      {report.checks?.length > 0 && (
        <div className="grid gap-2 sm:grid-cols-2">
          {report.checks.map((check) => (
            <div key={check.name} className="flex min-w-0 items-start gap-2 rounded-xl border border-line p-3 text-sm">
              <StatusPill value={check.passed ? "passed" : "failed"} />
              <div className="min-w-0"><p className="break-words font-medium text-ink">{check.name.replaceAll("_", " ")}</p>{check.details && <p className="mt-1 break-words text-xs text-muted">{check.details}</p>}</div>
            </div>
          ))}
        </div>
      )}
      {report.row_counts?.length > 0 && (
        <DataTable
          empty="No imported tables were reported."
          columns={[
            { key: "table", label: "Table" },
            { key: "expected", label: "Expected", render: (row) => formatNumber(row.expected) },
            { key: "imported", label: "Imported", render: (row) => row.imported === null ? "—" : formatNumber(row.imported) },
            { key: "current", label: "Current", render: (row) => formatNumber(row.current) },
            { key: "matches", label: "Snapshot", render: (row) => <StatusPill value={row.matches === true ? "matched" : row.matches === false ? "mismatch" : "unknown"} /> },
          ]}
          rows={report.row_counts}
        />
      )}
      {report.warnings?.length > 0 && (
        <Notice>
          <strong>Provenance/validation warnings:</strong>
          <ul className="mt-2 list-disc space-y-1 pl-5">{report.warnings.map((warning, index) => <li key={`${warning}-${index}`} className="break-words">{warning}</li>)}</ul>
        </Notice>
      )}
    </div>
  );
}

function Performance({ report, error }) {
  if (error) return <Notice>{error}</Notice>;
  if (!report?.measured) {
    return <p className="rounded-xl bg-ivory px-4 py-6 text-sm text-muted">Performance has not been measured. Run the documented API benchmark to populate these results.</p>;
  }
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <MetricCard label="Average response" value={`${report.average_response_ms?.toFixed(1) ?? "—"} ms`} icon={Clock3} />
      <MetricCard label="Median response" value={`${report.median_response_ms?.toFixed(1) ?? "—"} ms`} icon={Activity} tone="lavender" />
      <MetricCard label="95th percentile" value={`${report.p95_response_ms?.toFixed(1) ?? "—"} ms`} icon={BarChart3} tone="sand" />
      <MetricCard label="Successful requests" value={`${report.successful_request_percent?.toFixed(1) ?? "—"}%`} detail={`${formatNumber(report.total_tested_requests)} measured requests`} icon={ShieldCheck} />
      <p className="text-xs text-muted sm:col-span-2 xl:col-span-4">Maximum: {report.maximum_response_ms?.toFixed(1) ?? "—"} ms · Slowest route: {report.slowest_endpoint || "—"} · Tested: {report.last_tested_at ? new Date(report.last_tested_at).toLocaleString() : "—"}</p>
      {report.status_distribution && <p className="text-xs text-muted sm:col-span-2 xl:col-span-4">HTTP status distribution: {Object.entries(report.status_distribution).map(([status, count]) => `${status}: ${formatNumber(count)}`).join(" · ")}</p>}
    </div>
  );
}

export default function Analytics() {
  const [draft, setDraft] = useState(initialFilters);
  const [filters, setFilters] = useState(initialFilters);
  const [data, setData] = useState(null);
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true);
    const filterParams = Object.fromEntries(
      Object.entries(filters).filter(
        ([key, value]) => key !== "outcome" && value !== "",
      ),
    );
    const requests = {
      overview: api.get("/reports/overview"),
      lifecycle: api.get("/reports/credential-lifecycle", { params: filterParams }),
      verification: api.get("/reports/verification-analytics", {
        params: {
          ...(filters.date_from ? { date_from: filters.date_from } : {}),
          ...(filters.date_to ? { date_to: filters.date_to } : {}),
          ...(filters.outcome ? { outcome: filters.outcome } : {}),
        },
      }),
      academic: api.get("/reports/academic-analytics", {
        params: {
          ...(filters.date_from ? { date_from: filters.date_from } : {}),
          ...(filters.date_to ? { date_to: filters.date_to } : {}),
          ...(filters.course_id ? { course_id: filters.course_id } : {}),
          limit: 20,
        },
      }),
      quality: api.get("/reports/data-quality"),
      performance: api.get("/reports/performance"),
    };
    Promise.allSettled(Object.entries(requests).map(([, request]) => request))
      .then((results) => {
        if (!active) return;
        const nextData = {};
        const nextErrors = {};
        Object.keys(requests).forEach((key, index) => {
          const result = results[index];
          if (result.status === "fulfilled") nextData[key] = result.value.data;
          else nextErrors[key] = getErrorMessage(result.reason);
        });
        setData(nextData);
        setErrors(nextErrors);
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [filters]);

  function applyFilters(event) {
    event.preventDefault();
    setFilters({ ...draft });
  }

  function clearFilters() {
    setDraft(initialFilters);
    setFilters(initialFilters);
  }

  const overview = data?.overview;
  const lifecycle = data?.lifecycle;
  const verification = data?.verification;
  const academic = data?.academic;
  // List every month that has an issuance or a revocation. Revocations can fall in
  // months without issuances, and those months must not be dropped from the table.
  const issuedByPeriod = new Map((lifecycle?.issuance_over_time || []).map((row) => [row.period, row.count]));
  const revokedByPeriod = new Map((lifecycle?.revocations_over_time || []).map((row) => [row.period, row.count]));
  const timeRows = [...new Set([...issuedByPeriod.keys(), ...revokedByPeriod.keys()])].sort().map((period) => ({
    period,
    issued: issuedByPeriod.get(period) || 0,
    revoked: revokedByPeriod.get(period) || 0,
  }));

  return (
    <>
      <PageHeader
        eyebrow="Data & analytics"
        title="Credential insights"
        description="Live PostgreSQL aggregates, imported-data validation, and measured API performance. Analytics exclude the separate ground-truth files."
        action={<Button variant="secondary" onClick={() => setFilters({ ...filters })}><RefreshCw size={15} />Refresh</Button>}
      />
      <Card className="mb-5">
        <form onSubmit={applyFilters} className="grid gap-3 sm:grid-cols-2 xl:grid-cols-[1fr_1fr_1.4fr_1fr_1fr_auto_auto] xl:items-end">
          <Field label="From" type="date" value={draft.date_from} onChange={(event) => setDraft({ ...draft, date_from: event.target.value })} />
          <Field label="To" type="date" value={draft.date_to} onChange={(event) => setDraft({ ...draft, date_to: event.target.value })} />
          <Field label="Course ID (optional)" value={draft.course_id} onChange={(event) => setDraft({ ...draft, course_id: event.target.value })} placeholder="Course UUID" />
          <SelectField label="Credential status" value={draft.credential_status} onChange={(event) => setDraft({ ...draft, credential_status: event.target.value })}>
            <option value="">All statuses</option><option value="active">Active</option><option value="revoked">Revoked</option>
          </SelectField>
          <SelectField label="Verification outcome" value={draft.outcome} onChange={(event) => setDraft({ ...draft, outcome: event.target.value })}>
            <option value="">All outcomes</option><option value="VALID">Valid</option><option value="REVOKED">Revoked</option><option value="NOT_FOUND">Not found</option><option value="TAMPERED">Tampered</option><option value="INVALID_SIGNATURE">Invalid signature</option>
          </SelectField>
          <Button type="submit">Apply filters</Button>
          <Button type="button" variant="secondary" onClick={clearFilters}>Clear</Button>
        </form>
        <p className="mt-3 text-xs text-muted">Date, course, and credential-status filters apply where supported. Overview rates are all-time aggregates; verification outcome filters apply to verification analytics.</p>
      </Card>

      {loading && !data ? <LoadingState label="Loading live analytics…" /> : (
        <>
          {errors.overview && <div className="mb-4"><Notice>{errors.overview}</Notice></div>}
          {overview && (
            <>
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                <MetricCard label="Learners" value={formatNumber(overview.total_learners)} icon={Users} />
                <MetricCard label="Courses" value={formatNumber(overview.total_courses)} icon={BookOpen} tone="lavender" />
                <MetricCard label="Enrollments" value={formatNumber(overview.total_enrollments)} icon={BookOpen} tone="sand" />
                <MetricCard label="Completed records" value={formatNumber(overview.total_completed_records)} icon={BookOpen} />
                <MetricCard label="Eligible learners" value={formatNumber(overview.total_eligible_learners)} icon={ShieldCheck} tone="lavender" />
                <MetricCard label="Issued credentials" value={formatNumber(overview.total_credentials_issued)} icon={BadgeCheck} />
                <MetricCard label="Revoked credentials" value={formatNumber(overview.total_revoked_credentials)} icon={Activity} tone="sand" />
                <MetricCard label="Verification requests" value={formatNumber(overview.total_verification_requests)} icon={ShieldCheck} tone="sand" />
              </div>
              <div className="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                <RateCard label="Credential issuance rate" rate={overview.credential_issuance_rate} icon={BadgeCheck} />
                <RateCard label="Completion rate" rate={overview.completion_rate} icon={BookOpen} />
                <RateCard label="Revocation rate" rate={overview.revocation_rate} icon={Activity} />
                <RateCard label="Verification success rate" rate={overview.verification_success_rate} icon={ShieldCheck} />
              </div>
            </>
          )}

          <div className="mt-5 grid gap-4 xl:grid-cols-2">
            {errors.lifecycle ? <Notice>{errors.lifecycle}</Notice> : (
              <BarList title="Credential status" rows={lifecycle?.credential_status || []} />
            )}
            {errors.lifecycle ? <Notice>{errors.lifecycle}</Notice> : (
              <BarList title="Eligibility outcomes" rows={lifecycle?.eligibility_outcomes || []} />
            )}
            {errors.verification ? <Notice>{errors.verification}</Notice> : (
              <BarList title={`Verification outcomes · ${formatNumber(verification?.total_requests)} requests`} rows={verification?.outcome_counts || []} />
            )}
            {errors.verification ? <Notice>{errors.verification}</Notice> : (
              <BarList title="Verification modes" rows={verification?.mode_counts || []} />
            )}
          </div>

          <div className="mt-4 grid gap-4 xl:grid-cols-2">
            <Card>
              <h2 className="font-semibold text-ink">Issuance and revocations by month</h2>
              {errors.lifecycle ? <div className="mt-4"><Notice>{errors.lifecycle}</Notice></div> : (
                <DataTable
                  empty="No lifecycle activity matches the selected filters."
                  columns={[
                    { key: "period", label: "Month" },
                    { key: "issued", label: "Issued", render: (row) => formatNumber(row.issued) },
                    { key: "revoked", label: "Revoked", render: (row) => formatNumber(row.revoked) },
                  ]}
                  rows={timeRows}
                />
              )}
            </Card>
            {errors.academic ? <Notice>{errors.academic}</Notice> : (
              <Card>
                <h2 className="mb-4 font-semibold text-ink">Course activity</h2>
                <DataTable
                  empty="No course activity matches the selected filters."
                  columns={[
                    { key: "course_code", label: "Course" },
                    { key: "title", label: "Title" },
                    { key: "enrolled_learners", label: "Enrolled", render: (row) => formatNumber(row.enrolled_learners) },
                    { key: "completed_records", label: "Completed", render: (row) => formatNumber(row.completed_records) },
                  ]}
                  rows={academic?.course_distribution || []}
                />
              </Card>
            )}
          </div>
          <div className="mt-4 grid gap-4 xl:grid-cols-2">
            {errors.academic ? <Notice>{errors.academic}</Notice> : (
              <BarList
                title="Assessment score distribution"
                labelKey="range"
                rows={(academic?.assessment_score_distribution || []).map((row) => ({
                  ...row,
                  range: `${row.range} · ${row.score_scale}`,
                }))}
              />
            )}
            <Card>
              <div className="mb-4 flex items-center gap-2"><Database size={18} className="text-sage-800" /><h2 className="font-semibold text-ink">Dataset validation</h2></div>
              <DataQuality report={data?.quality} error={errors.quality} />
            </Card>
          </div>
          <Card className="mt-4">
            <div className="mb-4 flex items-center gap-2"><BarChart3 size={18} className="text-sage-800" /><h2 className="font-semibold text-ink">Measured API performance</h2></div>
            <Performance report={data?.performance} error={errors.performance} />
          </Card>
          {loading && <p className="mt-3 text-xs text-muted">Refreshing analytics…</p>}
          {Object.keys(errors).length > 0 && <p className="mt-3 text-xs text-muted">Some panels could not be loaded. Other successful API panels remain visible.</p>}
        </>
      )}
    </>
  );
}
