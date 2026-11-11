import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, Check, Plus, RefreshCw } from "lucide-react";
import { Button, Card, DataTable, Field, LoadingState, Notice, PageHeader, SearchBox, SelectField, StatusPill } from "../components/common/ui.jsx";
import useResource from "../hooks/useResource.js";
import { useAuth } from "../context/AuthContext.jsx";
import api, { getErrorMessage } from "../services/api.js";

const academics = ["PLATFORM_ADMINISTRATOR", "ACADEMIC_ADMINISTRATOR"];
const canManage = (user) => user?.roles?.some((role) => academics.includes(role));
const canIssue = (user) => user?.roles?.includes("ACADEMIC_ADMINISTRATOR");

function ResourcePanel({ resource, columns, searchPlaceholder, empty, children }) {
  const [search, setSearch] = useState("");
  const filtered = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return needle ? resource.items.filter((item) => JSON.stringify(item).toLowerCase().includes(needle)) : resource.items;
  }, [resource.items, search]);
  return (
    <>
      {children}
      <Card>
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div><h2 className="font-semibold text-ink">Records</h2><p className="mt-1 text-xs text-muted">Showing {filtered.length} loaded record{filtered.length === 1 ? "" : "s"}.</p></div>
          <div className="flex items-center gap-2"><SearchBox value={search} onChange={setSearch} placeholder={searchPlaceholder} /><Button variant="secondary" className="px-3" onClick={resource.reload} aria-label="Refresh records"><RefreshCw size={16} /></Button></div>
        </div>
        {resource.error && <div className="mb-4"><Notice>{resource.error}</Notice></div>}
        {resource.loading && !resource.items.length ? <LoadingState /> : <DataTable columns={columns} rows={filtered} empty={empty} />}
        {resource.hasMore && <div className="mt-4 text-center"><Button variant="secondary" disabled={resource.loading} onClick={resource.loadMore}>{resource.loading ? "Loading…" : "Load next 50"}</Button></div>}
      </Card>
    </>
  );
}

function MutationFeedback({ error, success }) {
  if (error) return <Notice>{error}</Notice>;
  if (success) return <Notice tone="success">{success}</Notice>;
  return null;
}

function Learners() {
  const resource = useResource("/learners");
  const [name, setName] = useState("");
  const [learnerId, setLearnerId] = useState("");
  const [editing, setEditing] = useState(null);
  const [selected, setSelected] = useState(null);
  const [detailsId, setDetailsId] = useState(null);
  const [detailsError, setDetailsError] = useState("");
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [saving, setSaving] = useState(false);
  const { user } = useAuth();
  async function submit(event) {
    event.preventDefault(); setError(""); setSuccess(""); setSaving(true);
    try {
      if (editing) await api.patch(`/learners/${editing.id}`, { display_name: name.trim() });
      else await api.post("/learners", { display_name: name.trim(), ...(learnerId.trim() ? { learner_id: learnerId.trim() } : {}) });
      setName(""); setLearnerId(""); setEditing(null); setSuccess(editing ? "Learner profile updated." : "Learner record created."); await resource.reload();
    } catch (requestError) { setError(getErrorMessage(requestError)); } finally { setSaving(false); }
  }
  async function showDetails(row) {
    setDetailsError(""); setDetailsId(row.id); setDetailsLoading(true);
    try { const { data } = await api.get(`/learners/${row.id}`); setSelected(data); }
    catch (requestError) { setDetailsError(getErrorMessage(requestError)); }
    finally { setDetailsLoading(false); setDetailsId(null); }
  }
  const columns = [
    { key: "learner_id", label: "Learner ID" },
    { key: "display_name", label: "Name" },
    { key: "archived_at", label: "Status", render: (row) => <StatusPill value={row.archived_at ? "archived" : "active"} /> },
    { key: "details", label: "", render: (row) => <button className="text-sm font-semibold text-sage-800 hover:underline" onClick={() => showDetails(row)}>{detailsLoading && detailsId === row.id ? "Loading…" : "Details"}</button> },
    ...(canManage(user) ? [{ key: "actions", label: "", render: (row) => <button className="text-sm font-semibold text-sage-800 hover:underline" onClick={() => { setEditing(row); setName(row.display_name); setLearnerId(row.learner_id); setSuccess(""); setError(""); }}>Edit</button> }] : []),
  ];
  return <>
    <PageHeader eyebrow="Academic records" title="Learners" description="Browse learner profiles and maintain their institutional names and identifiers." />
    <ResourcePanel resource={resource} columns={columns} searchPlaceholder="Search learners" empty="No learner records yet.">
      {selected && <Card className="mb-5">
        <div className="flex items-start justify-between gap-3"><div><p className="text-xs font-bold uppercase tracking-wider text-muted">Learner profile</p><h2 className="mt-1 font-semibold text-ink">{selected.display_name}</h2></div><Button variant="secondary" onClick={() => setSelected(null)}>Close</Button></div>
        <dl className="mt-4 grid gap-4 sm:grid-cols-3">
          <div><dt className="text-xs text-muted">Learner ID</dt><dd className="mt-1 text-sm font-medium text-ink">{selected.learner_id}</dd></div>
          <div><dt className="text-xs text-muted">Profile status</dt><dd className="mt-1"><StatusPill value={selected.archived_at ? "archived" : "active"} /></dd></div>
          <div><dt className="text-xs text-muted">Linked account</dt><dd className="mt-1 break-all font-mono text-xs text-ink">{selected.user_id || "Not linked"}</dd></div>
        </dl>
        {detailsError && <div className="mt-3"><Notice>{detailsError}</Notice></div>}
      </Card>}
      {detailsError && !selected && <div className="mb-5"><Notice>{detailsError}</Notice></div>}
      {canManage(user) && <Card className="mb-5">
        <h2 className="mb-4 font-semibold text-ink">{editing ? "Update learner" : "Add a learner"}</h2>
        <form onSubmit={submit} className="grid gap-4 md:grid-cols-[1fr_1fr_auto] md:items-end">
          <Field label="Display name" value={name} onChange={(event) => setName(event.target.value)} required maxLength={200} />
          <Field label="Learner ID (optional)" value={learnerId} onChange={(event) => setLearnerId(event.target.value)} disabled={Boolean(editing)} placeholder="LRN-000001" pattern="LRN-[0-9]{6}" />
          <div className="flex gap-2"><Button disabled={saving}>{saving ? "Saving…" : editing ? "Save changes" : <><Plus size={16} /> Create learner</>}</Button>{editing && <Button variant="secondary" type="button" onClick={() => { setEditing(null); setName(""); }}>Cancel</Button>}</div>
        </form>
        <div className="mt-3"><MutationFeedback error={error} success={success} /></div>
      </Card>}
    </ResourcePanel>
  </>;
}

function Courses() {
  const resource = useResource("/courses");
  const { user } = useAuth();
  const [selected, setSelected] = useState(null);
  const [form, setForm] = useState({ course_code: "", title: "", description: "" });
  const [editing, setEditing] = useState(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [saving, setSaving] = useState(false);
  async function submit(event) {
    event.preventDefault(); setError(""); setSuccess(""); setSaving(true);
    const payload = { title: form.title.trim(), description: form.description.trim() || null };
    try {
      if (editing) await api.patch(`/courses/${editing.id}`, payload);
      else await api.post("/courses", { ...payload, course_code: form.course_code.trim(), status: "active" });
      setForm({ course_code: "", title: "", description: "" }); setEditing(null); setSuccess(editing ? "Course updated." : "Course created."); await resource.reload();
    } catch (requestError) { setError(getErrorMessage(requestError)); } finally { setSaving(false); }
  }
  const columns = [
    { key: "course_code", label: "Course code" }, { key: "title", label: "Course title" },
    { key: "status", label: "Status", render: (row) => <StatusPill value={row.status} /> },
    { key: "effective_from", label: "Effective from", render: (row) => row.effective_from ? new Date(row.effective_from).toLocaleDateString() : "—" },
    { key: "details", label: "", render: (row) => <button className="text-sm font-semibold text-sage-800 hover:underline" onClick={() => setSelected(row)}>Details</button> },
    ...(canManage(user) ? [{ key: "actions", label: "", render: (row) => <button className="text-sm font-semibold text-sage-800 hover:underline" onClick={() => { setEditing(row); setForm({ course_code: row.course_code, title: row.title, description: row.description || "" }); setError(""); setSuccess(""); }}>Edit</button> }] : []),
  ];
  return <>
    <PageHeader eyebrow="Academic records" title="Courses" description="Maintain the course catalogue used by enrollment and credential rules." />
    <ResourcePanel resource={resource} columns={columns} searchPlaceholder="Search courses" empty="No courses in the catalogue.">
      {selected && <Card className="mb-5">
        <div className="flex items-start justify-between gap-3"><div><p className="text-xs font-bold uppercase tracking-wider text-muted">Course details</p><h2 className="mt-1 font-semibold text-ink">{selected.title}</h2></div><Button variant="secondary" onClick={() => setSelected(null)}>Close</Button></div>
        <dl className="mt-4 grid gap-4 sm:grid-cols-2">
          <div><dt className="text-xs text-muted">Course code</dt><dd className="mt-1 text-sm font-medium text-ink">{selected.course_code}</dd></div>
          <div><dt className="text-xs text-muted">Status</dt><dd className="mt-1"><StatusPill value={selected.status} /></dd></div>
          <div><dt className="text-xs text-muted">Description</dt><dd className="mt-1 text-sm text-ink">{selected.description || "No description"}</dd></div>
          <div><dt className="text-xs text-muted">Effective period</dt><dd className="mt-1 text-sm text-ink">{selected.effective_from ? new Date(selected.effective_from).toLocaleString() : "Not specified"} – {selected.effective_to ? new Date(selected.effective_to).toLocaleString() : "open"}</dd></div>
        </dl>
      </Card>}
      {canManage(user) && <Card className="mb-5">
        <h2 className="mb-4 font-semibold text-ink">{editing ? "Update course" : "Add a course"}</h2>
        <form onSubmit={submit} className="grid gap-4 md:grid-cols-2">
          {!editing && <Field label="Course code" value={form.course_code} onChange={(event) => setForm({ ...form, course_code: event.target.value })} required maxLength={64} />}
          <Field label="Title" value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} required maxLength={200} />
          <Field label="Description" value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} maxLength={2000} className="md:col-span-2" />
          <div className="flex gap-2 md:col-span-2"><Button disabled={saving}>{saving ? "Saving…" : editing ? "Save changes" : <><Plus size={16} /> Create course</>}</Button>{editing && <Button variant="secondary" type="button" onClick={() => { setEditing(null); setForm({ course_code: "", title: "", description: "" }); }}>Cancel</Button>}</div>
        </form>
        <div className="mt-3"><MutationFeedback error={error} success={success} /></div>
      </Card>}
    </ResourcePanel>
  </>;
}

function CredentialRules() {
  const resource = useResource("/credential-rules");
  const courses = useResource("/courses");
  const { user } = useAuth();
  const [form, setForm] = useState({ rule_code: "", name: "", course_id: "", minimum_score: "" });
  const [versionRule, setVersionRule] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [saving, setSaving] = useState(false);
  const rules = [...new Map(resource.items.map((row) => [row.rule_code, row])).values()];
  async function submit(event) {
    event.preventDefault(); setError(""); setSuccess(""); setSaving(true);
    const criteria = { requires_completion: true, ...(form.minimum_score !== "" ? { minimum_score: Number(form.minimum_score), score_scale: "0-100" } : {}) };
    const body = { course_id: form.course_id, criteria, attempt_selection_policy: "latest_graded", effective_from: new Date().toISOString() };
    try {
      if (versionRule) {
        await api.post(`/credential-rules/${encodeURIComponent(versionRule)}/versions`, body);
        setSuccess(`A new version of ${versionRule} was scheduled effective immediately.`);
      } else {
        await api.post("/credential-rules", { ...body, rule_code: form.rule_code.trim(), name: form.name.trim() });
        setSuccess("Credential rule created.");
      }
      setForm({ rule_code: "", name: "", course_id: "", minimum_score: "" }); setVersionRule(""); await resource.reload();
    } catch (requestError) { setError(getErrorMessage(requestError)); } finally { setSaving(false); }
  }
  const columns = [
    { key: "rule_code", label: "Rule" }, { key: "name", label: "Name" },
    { key: "version_number", label: "Version", render: (row) => `v${row.version_number}` },
    { key: "course_id", label: "Course ID", render: (row) => <code className="text-xs">{row.course_id}</code> },
    { key: "criteria", label: "Criteria", render: (row) => <span className="break-all text-xs">{JSON.stringify(row.criteria)}</span> },
    { key: "effective_from", label: "Effective from", render: (row) => new Date(row.effective_from).toLocaleString() },
    { key: "status", label: "Status", render: (row) => <StatusPill value={row.status} /> },
  ];
  return <>
    <PageHeader eyebrow="Eligibility configuration" title="Credential rules" description="Rules are versioned and immutable. New versions use the active course scope and the backend's latest-graded assessment policy." />
    <ResourcePanel resource={resource} columns={columns} searchPlaceholder="Search credential rules" empty="No credential rules configured.">
      {canManage(user) && <Card className="mb-5">
        <h2 className="mb-4 font-semibold text-ink">{versionRule ? `New version: ${versionRule}` : "Configure a rule"}</h2>
        <form onSubmit={submit} className="grid gap-4 md:grid-cols-2">
          {versionRule ? <SelectField label="Rule to version" value={versionRule} onChange={(event) => setVersionRule(event.target.value)} required><option value="">Select a rule</option>{rules.map((rule) => <option key={rule.rule_code} value={rule.rule_code}>{rule.rule_code} — {rule.name}</option>)}</SelectField> : <>
            <Field label="Rule code" value={form.rule_code} onChange={(event) => setForm({ ...form, rule_code: event.target.value })} required maxLength={64} />
            <Field label="Rule name" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required maxLength={200} />
          </>}
          <SelectField label="Required course" value={form.course_id} onChange={(event) => setForm({ ...form, course_id: event.target.value })} required><option value="">Select a course</option>{courses.items.map((course) => <option key={course.id} value={course.id}>{course.course_code} — {course.title}</option>)}</SelectField>
          <Field label="Minimum assessment score (optional, 0–100)" type="number" min="0" max="100" step="0.01" value={form.minimum_score} onChange={(event) => setForm({ ...form, minimum_score: event.target.value })} />
          {courses.error && <div className="md:col-span-2"><Notice>{courses.error}</Notice></div>}
          <div className="flex flex-wrap gap-2 md:col-span-2"><Button disabled={saving || !courses.items.length}>{saving ? "Saving…" : <><Plus size={16} /> {versionRule ? "Create version" : "Create rule"}</>}</Button>{!versionRule && rules.length > 0 && <Button type="button" variant="secondary" onClick={() => { setVersionRule(rules[0].rule_code); setError(""); setSuccess(""); }}>Create a version</Button>}{versionRule && <Button type="button" variant="secondary" onClick={() => setVersionRule("")}>Cancel</Button>}</div>
        </form>
        <div className="mt-3"><MutationFeedback error={error} success={success} /></div>
      </Card>}
    </ResourcePanel>
  </>;
}

function Completions() {
  const learners = useResource("/learners");
  const courses = useResource("/courses");
  const enrollments = useResource("/enrollments");
  const completions = useResource("/completions");
  const attempts = useResource("/assessment-attempts");
  const { user } = useAuth();
  const [enrollForm, setEnrollForm] = useState({ learner_id: "", course_id: "" });
  const [completionForm, setCompletionForm] = useState({ enrollment_id: "", status: "completed" });
  const [attemptForm, setAttemptForm] = useState({ completion_record_id: "", assessment_key: "", score: "" });
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [saving, setSaving] = useState("");
  const canWrite = user?.roles?.some((role) => ["PLATFORM_ADMINISTRATOR", "ACADEMIC_ADMINISTRATOR"].includes(role));
  async function mutate(label, request, reset) {
    setError(""); setSuccess(""); setSaving(label);
    try {
      await request(); reset(); setSuccess(`${label} recorded successfully.`);
      await Promise.all([enrollments.reload(), completions.reload(), attempts.reload()]);
    } catch (requestError) { setError(getErrorMessage(requestError)); } finally { setSaving(""); }
  }
  const columns = [
    { key: "learner_id", label: "Learner" }, { key: "course_id", label: "Course" },
    { key: "status", label: "Status", render: (row) => <StatusPill value={row.status} /> },
    { key: "completed_at", label: "Completed", render: (row) => row.completed_at ? new Date(row.completed_at).toLocaleString() : "—" },
  ];
  return <>
    <PageHeader eyebrow="Learning records" title="Enrollments & completions" description="Record enrollment, course status, and assessment attempts. Assessment history is retained by the backend." />
    {canWrite && <div className="mb-5 grid gap-5 xl:grid-cols-3">
      <Card><h2 className="mb-4 font-semibold text-ink">Enroll learner</h2><form className="space-y-4" onSubmit={(event) => { event.preventDefault(); mutate("Enrollment", () => api.post("/enrollments", enrollForm), () => setEnrollForm({ learner_id: "", course_id: "" })); }}>
        <SelectField label="Learner" value={enrollForm.learner_id} onChange={(event) => setEnrollForm({ ...enrollForm, learner_id: event.target.value })} required><option value="">Select learner</option>{learners.items.map((item) => <option key={item.id} value={item.id}>{item.learner_id} — {item.display_name}</option>)}</SelectField>
        <SelectField label="Course" value={enrollForm.course_id} onChange={(event) => setEnrollForm({ ...enrollForm, course_id: event.target.value })} required><option value="">Select course</option>{courses.items.map((item) => <option key={item.id} value={item.id}>{item.course_code} — {item.title}</option>)}</SelectField>
        <Button disabled={Boolean(saving) || !learners.items.length || !courses.items.length}>{saving === "Enrollment" ? "Saving…" : "Create enrollment"}</Button>
      </form></Card>
      <Card><h2 className="mb-4 font-semibold text-ink">Record completion</h2><form className="space-y-4" onSubmit={(event) => { event.preventDefault(); mutate("Completion", () => api.post("/completions", { ...completionForm, ...(completionForm.status === "completed" ? { completed_at: new Date().toISOString() } : {}) }), () => setCompletionForm({ enrollment_id: "", status: "completed" })); }}>
        <SelectField label="Enrollment" value={completionForm.enrollment_id} onChange={(event) => setCompletionForm({ ...completionForm, enrollment_id: event.target.value })} required><option value="">Select enrollment</option>{enrollments.items.map((item) => <option key={item.id} value={item.id}>{item.id} · learner {item.learner_id}</option>)}</SelectField>
        <SelectField label="Status" value={completionForm.status} onChange={(event) => setCompletionForm({ ...completionForm, status: event.target.value })}><option value="completed">Completed</option><option value="in_progress">In progress</option><option value="failed">Failed</option></SelectField>
        <Button disabled={Boolean(saving) || !enrollments.items.length}>{saving === "Completion" ? "Saving…" : "Record completion"}</Button>
      </form></Card>
      <Card><h2 className="mb-4 font-semibold text-ink">Assessment attempt</h2><form className="space-y-4" onSubmit={(event) => { event.preventDefault(); const now = new Date().toISOString(); mutate("Assessment attempt", () => api.post("/assessment-attempts", { completion_record_id: attemptForm.completion_record_id, assessment_key: attemptForm.assessment_key.trim(), score: attemptForm.score === "" ? null : Number(attemptForm.score), score_scale: "0-100", status: "graded", submitted_at: now, graded_at: now }), () => setAttemptForm({ completion_record_id: "", assessment_key: "", score: "" })); }}>
        <SelectField label="Completion record" value={attemptForm.completion_record_id} onChange={(event) => setAttemptForm({ ...attemptForm, completion_record_id: event.target.value })} required><option value="">Select completion</option>{completions.items.map((item) => <option key={item.id} value={item.id}>{item.id} · learner {item.learner_id}</option>)}</SelectField>
        <Field label="Assessment key" value={attemptForm.assessment_key} onChange={(event) => setAttemptForm({ ...attemptForm, assessment_key: event.target.value })} required maxLength={100} />
        <Field label="Score (0–100)" type="number" min="0" max="100" step="0.01" value={attemptForm.score} onChange={(event) => setAttemptForm({ ...attemptForm, score: event.target.value })} />
        <Button disabled={Boolean(saving) || !completions.items.length}>{saving === "Assessment attempt" ? "Saving…" : "Record attempt"}</Button>
      </form></Card>
      {(learners.error || courses.error || enrollments.error || completions.error || attempts.error) && <div className="xl:col-span-3"><Notice>{[learners.error, courses.error, enrollments.error, completions.error, attempts.error].filter(Boolean).join(" ")}</Notice></div>}
      <div className="xl:col-span-3"><MutationFeedback error={error} success={success} /></div>
    </div>}
    <ResourcePanel resource={completions} columns={columns} searchPlaceholder="Search completion records" empty="No completion records have been recorded." />
    <Card className="mt-5">
      <h2 className="mb-4 font-semibold text-ink">Recent assessment attempts</h2>
      <DataTable empty="No assessment attempts recorded." columns={[
        { key: "assessment_key", label: "Assessment" }, { key: "attempt_number", label: "Attempt" },
        { key: "score", label: "Score" }, { key: "status", label: "Status", render: (row) => <StatusPill value={row.status} /> },
        { key: "submitted_at", label: "Submitted", render: (row) => new Date(row.submitted_at).toLocaleString() },
      ]} rows={attempts.items} />
      {attempts.error && <div className="mt-3"><Notice>{attempts.error}</Notice></div>}
    </Card>
  </>;
}

function Eligibility() {
  const learners = useResource("/learners");
  const rules = useResource("/credential-rules");
  const availableRules = [...new Map(rules.items.map((row) => [row.rule_code, row])).values()];
  const [form, setForm] = useState({ learner_id: "", rule_code: "" });
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  async function submit(event) {
    event.preventDefault(); setError(""); setResult(null); setLoading(true);
    try { const { data } = await api.post("/eligibility/evaluate", form); setResult(data); }
    catch (requestError) { setError(getErrorMessage(requestError)); }
    finally { setLoading(false); }
  }
  return <>
    <PageHeader eyebrow="Decisioning" title="Eligibility evaluation" description="Evaluate current completion and assessment evidence against the effective version of a credential rule." />
    <div className="grid gap-5 lg:grid-cols-[.9fr_1.1fr]">
      <Card><h2 className="mb-4 font-semibold text-ink">Evaluate learner</h2><form className="space-y-4" onSubmit={submit}>
        <SelectField label="Learner" value={form.learner_id} onChange={(event) => setForm({ ...form, learner_id: event.target.value })} required><option value="">Select learner</option>{learners.items.map((item) => <option key={item.id} value={item.id}>{item.learner_id} — {item.display_name}</option>)}</SelectField>
        <SelectField label="Credential rule" value={form.rule_code} onChange={(event) => setForm({ ...form, rule_code: event.target.value })} required><option value="">Select rule</option>{availableRules.map((item) => <option key={item.rule_code} value={item.rule_code}>{item.rule_code} — {item.name}</option>)}</SelectField>
        {(learners.error || rules.error) && <Notice>{learners.error || rules.error}</Notice>}
        <Button disabled={loading || !learners.items.length || !availableRules.length}>{loading ? "Evaluating evidence…" : "Evaluate eligibility"}</Button>
      </form></Card>
      <Card className="min-h-64">
        {error ? <Notice>{error}</Notice> : result ? <><div className="flex flex-wrap items-center justify-between gap-3"><h2 className="font-semibold text-ink">Decision result</h2><StatusPill value={result.outcome} /></div><dl className="mt-5 grid gap-4 sm:grid-cols-2"><div><dt className="text-xs text-muted">Rule</dt><dd className="mt-1 font-medium text-ink">{result.rule_code}</dd></div><div><dt className="text-xs text-muted">Evaluated</dt><dd className="mt-1 text-sm text-ink">{new Date(result.evaluated_at).toLocaleString()}</dd></div><div className="sm:col-span-2"><dt className="text-xs text-muted">Rule version</dt><dd className="mt-1 break-all font-mono text-xs text-ink">{result.rule_version_id}</dd></div></dl><div className="mt-5"><p className="text-xs font-semibold uppercase tracking-wide text-muted">Failed requirements</p>{result.reason_codes?.length ? <ul className="mt-2 space-y-2">{result.reason_codes.map((reason) => <li key={reason} className="flex items-start gap-2 text-sm text-rose-800"><AlertTriangle size={16} className="mt-0.5 shrink-0" />{reason.replaceAll("_", " ")}</li>)}</ul> : <p className="mt-2 flex items-center gap-2 text-sm text-sage-900"><Check size={16} />All evaluated requirements were met.</p>}</div><p className="mt-4 text-xs leading-5 text-muted">Decision ID: <code>{result.decision_id}</code></p></> : <div className="flex h-full min-h-56 flex-col items-center justify-center text-center"><span className="grid size-12 place-items-center rounded-2xl bg-ivory text-muted"><Check size={22} /></span><p className="mt-4 font-medium text-ink">No decision yet</p><p className="mt-1 text-sm text-muted">Choose a learner and rule to evaluate current evidence.</p></div>}
      </Card>
    </div>
  </>;
}

function Credentials() {
  const { user } = useAuth();
  const learner = user?.roles?.includes("LEARNER");
  const resource = useResource(learner ? "/learners/me/credentials" : "/credentials");
  const learners = useResource("/learners");
  const rules = useResource("/credential-rules");
  const [form, setForm] = useState({ learner_id: "", rule_code: "" });
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [saving, setSaving] = useState(false);
  const rulesByCode = [...new Map(rules.items.map((row) => [row.rule_code, row])).values()];
  async function issue(event) {
    event.preventDefault(); setError(""); setSuccess(""); setSaving(true);
    try {
      const { data } = await api.post("/credentials/issue", form, { headers: { "Idempotency-Key": window.crypto.randomUUID() } });
      setSuccess(`Credential ${data.credential_id} was issued successfully.`);
      setForm({ learner_id: "", rule_code: "" }); await resource.reload();
    } catch (requestError) { setError(getErrorMessage(requestError)); }
    finally { setSaving(false); }
  }
  const columns = [
    { key: "credential_id", label: "Credential ID", render: (row) => <code className="font-semibold">{row.credential_id}</code> },
    { key: "issued_at", label: "Issued", render: (row) => new Date(row.issued_at).toLocaleDateString() },
    { key: "signature_algorithm", label: "Signature" },
    { key: "sha256_digest", label: "SHA-256", render: (row) => <span title={row.sha256_digest} className="font-mono text-xs">{row.sha256_digest?.slice(0, 18)}…</span> },
    { key: "replacement_of_credential_id", label: "Replaces", render: (row) => row.replacement_of_credential_id || "—" },
  ];
  return <>
    <PageHeader eyebrow="Credential lifecycle" title={learner ? "My credentials" : "Credentials"} description={learner ? "Credentials linked to your learner account." : "Review issued credentials. Issuance re-evaluates eligibility and is protected against duplicate submissions."} />
    {canIssue(user) && <Card className="mb-5">
      <h2 className="mb-4 font-semibold text-ink">Issue a credential</h2>
      <form onSubmit={issue} className="grid gap-4 md:grid-cols-[1fr_1fr_auto] md:items-end">
        <SelectField label="Learner" value={form.learner_id} onChange={(event) => setForm({ ...form, learner_id: event.target.value })} required><option value="">Select learner</option>{learners.items.map((item) => <option key={item.id} value={item.id}>{item.learner_id} — {item.display_name}</option>)}</SelectField>
        <SelectField label="Rule" value={form.rule_code} onChange={(event) => setForm({ ...form, rule_code: event.target.value })} required><option value="">Select rule</option>{rulesByCode.map((item) => <option key={item.rule_code} value={item.rule_code}>{item.rule_code} — {item.name}</option>)}</SelectField>
        <Button disabled={saving || !learners.items.length || !rulesByCode.length}>{saving ? "Evaluating & issuing…" : "Issue credential"}</Button>
      </form>
      <div className="mt-3"><MutationFeedback error={error} success={success} /></div>
      {(learners.error || rules.error) && <div className="mt-3"><Notice>{learners.error || rules.error}</Notice></div>}
    </Card>}
    <ResourcePanel resource={resource} columns={columns} searchPlaceholder="Search credentials" empty="No credentials are available for this account." />
  </>;
}

function Revocations() {
  const resource = useResource("/revocations");
  const credentials = useResource("/credentials");
  const revokedCredentialIds = new Set(resource.items.map((row) => row.credential_id));
  const [form, setForm] = useState({ credential_id: "", reason_code: "", reason_detail: "" });
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [saving, setSaving] = useState(false);
  async function revoke() {
    setSaving(true); setError(""); setSuccess("");
    try {
      await api.post(`/revocations/${encodeURIComponent(form.credential_id)}`, { reason_code: form.reason_code.trim(), reason_detail: form.reason_detail.trim() || null });
      setSuccess(`Credential ${form.credential_id} has been revoked.`); setForm({ credential_id: "", reason_code: "", reason_detail: "" }); setConfirming(false); await resource.reload();
    } catch (requestError) { setError(getErrorMessage(requestError)); }
    finally { setSaving(false); }
  }
  return <>
    <PageHeader eyebrow="Credential lifecycle" title="Revocations" description="Revocation is permanent and preserves the credential and its audit history." />
    <Card className="mb-5">
      <h2 className="mb-4 font-semibold text-ink">Revoke a credential</h2>
      {!confirming ? <form onSubmit={(event) => { event.preventDefault(); setError(""); setConfirming(true); }} className="grid gap-4 md:grid-cols-3 md:items-end">
        <SelectField label="Credential" value={form.credential_id} onChange={(event) => setForm({ ...form, credential_id: event.target.value })} required><option value="">Select credential</option>{credentials.items.filter((item) => !revokedCredentialIds.has(item.id)).map((item) => <option key={item.id} value={item.credential_id}>{item.credential_id}</option>)}</SelectField>
        <Field label="Reason code" value={form.reason_code} onChange={(event) => setForm({ ...form, reason_code: event.target.value })} required maxLength={64} placeholder="e.g. awarded_in_error" />
        <Field label="Reason detail (optional)" value={form.reason_detail} onChange={(event) => setForm({ ...form, reason_detail: event.target.value })} maxLength={1000} />
        <div className="md:col-span-3"><Button variant="danger" disabled={!credentials.items.length}>Continue to confirmation</Button></div>
      </form> : <div className="rounded-xl border border-rose-200 bg-rose-50 p-4"><p className="font-semibold text-rose-900">Confirm revocation of {form.credential_id}?</p><p className="mt-1 text-sm text-rose-800">This action cannot be undone. The credential will remain in the audit history.</p><div className="mt-4 flex gap-2"><Button variant="danger" disabled={saving} onClick={revoke}>{saving ? "Revoking…" : "Confirm revocation"}</Button><Button variant="secondary" onClick={() => setConfirming(false)}>Cancel</Button></div></div>}
      <div className="mt-3"><MutationFeedback error={error} success={success} /></div>
      {credentials.error && <div className="mt-3"><Notice>{credentials.error}</Notice></div>}
    </Card>
    <ResourcePanel resource={resource} columns={[
      { key: "credential_id", label: "Credential", render: (row) => credentials.items.find((item) => item.id === row.credential_id)?.credential_id || row.credential_id }, { key: "reason_code", label: "Reason" },
      { key: "actor_reference", label: "Actor" }, { key: "effective_at", label: "Effective", render: (row) => new Date(row.effective_at).toLocaleString() },
    ]} searchPlaceholder="Search revocations" empty="No revocations recorded." />
  </>;
}

function Audit() {
  const [target, setTarget] = useState("");
  const resource = useResource("/audit", target.trim() ? { target_reference: target.trim() } : {});
  return <>
    <PageHeader eyebrow="Governance" title="Audit history" description="Append-only events from lifecycle operations, ordered by occurrence time." />
    <ResourcePanel resource={resource} searchPlaceholder="Search loaded audit events" empty="No audit events match the current filter." columns={[
      { key: "event_type", label: "Event" }, { key: "outcome", label: "Outcome", render: (row) => <StatusPill value={row.outcome} /> },
      { key: "actor_reference", label: "Actor" }, { key: "target_reference", label: "Target" },
      { key: "occurred_at", label: "Occurred", render: (row) => new Date(row.occurred_at).toLocaleString() },
      { key: "reason_code", label: "Reason" },
    ]}>
      <Card className="mb-5"><div className="flex flex-wrap items-end gap-3"><Field className="min-w-[220px] flex-1" label="Filter by exact target reference" value={target} onChange={(event) => setTarget(event.target.value)} placeholder="Credential ID, learner ID, or rule code" /><Button variant="secondary" onClick={resource.reload}>Apply filter</Button></div></Card>
    </ResourcePanel>
  </>;
}

function Reports() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  async function load() {
    setLoading(true); setError("");
    const paths = ["/reports/summary", "/reports/issuance", "/reports/revocations", "/reports/verification"];
    const results = await Promise.allSettled(paths.map((path) => api.get(path)));
    const failed = results.find((result) => result.status === "rejected");
    if (failed) setError(getErrorMessage(failed.reason));
    if (results.every((result) => result.status === "fulfilled")) setData(results.map((result) => result.value.data));
    setLoading(false);
  }
  useEffect(() => { load(); }, []);
  const [summary, issuance, revocations, verification] = data || [];
  return <>
    <PageHeader eyebrow="Insights" title="Reports" description="Summary and grouped counts returned by the reporting API." action={<Button variant="secondary" onClick={load}><RefreshCw size={15} /> Refresh</Button>} />
    {loading ? <LoadingState label="Loading reports…" /> : error ? <Notice>{error}</Notice> : data && <>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{[
        ["Total credentials", summary.total_credentials], ["Active credentials", summary.credentials_by_status?.active ?? 0],
        ["Revocations", summary.total_revocations], ["Verification requests", summary.total_verifications],
      ].map(([label, value]) => <Card key={label}><p className="text-sm text-muted">{label}</p><p className="mt-3 text-3xl font-semibold text-ink">{value.toLocaleString()}</p></Card>)}</div>
      <div className="mt-5 grid gap-5 xl:grid-cols-3">
        <Card><h2 className="mb-4 font-semibold text-ink">Issuance by year</h2><DataTable columns={[{ key: "year", label: "Year" }, { key: "count", label: "Credentials" }]} rows={Object.entries(issuance.by_year || {}).map(([year, count]) => ({ year, count }))} empty="No issuance data." /></Card>
        <Card><h2 className="mb-4 font-semibold text-ink">Revocations by reason</h2><DataTable columns={[{ key: "reason", label: "Reason" }, { key: "count", label: "Records" }]} rows={Object.entries(revocations.by_reason || {}).map(([reason, count]) => ({ reason, count }))} empty="No revocation data." /></Card>
        <Card><h2 className="mb-4 font-semibold text-ink">Verification outcomes</h2><DataTable columns={[{ key: "mode", label: "Mode" }, { key: "outcome", label: "Outcome" }, { key: "count", label: "Count" }]} rows={verification.groups || []} empty="No verification data." /></Card>
      </div>
    </>}
  </>;
}

export default function Workspace({ page }) {
  const pages = {
    learners: [Learners, "Learners"], courses: [Courses, "Courses"], rules: [CredentialRules, "Credential rules"],
    completions: [Completions, "Enrollments & completions"], eligibility: [Eligibility, "Eligibility"],
    credentials: [Credentials, "Credentials"], revocations: [Revocations, "Revocations"], audit: [Audit, "Audit"], reports: [Reports, "Reports"],
  };
  const [Component] = pages[page] || [Learners];
  return <Component />;
}
