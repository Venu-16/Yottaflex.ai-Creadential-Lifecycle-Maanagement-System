import { useEffect, useState } from "react";
import { Activity, BadgeCheck, BookOpen, ClipboardCheck, Users } from "lucide-react";
import { Link } from "react-router-dom";
import { Card, DataTable, LoadingState, Notice, PageHeader } from "../../components/common/ui.jsx";
import { useAuth } from "../../context/AuthContext.jsx";
import api, { getErrorMessage } from "../../services/api.js";

const cards = [
  { key: "total_credentials", label: "Credentials issued", icon: BadgeCheck, tone: "sage" },
  { key: "active", label: "Currently active", icon: ClipboardCheck, tone: "lavender" },
  { key: "total_revocations", label: "Revocations", icon: Activity, tone: "sand" },
  { key: "total_verifications", label: "Verification checks", icon: BookOpen, tone: "sage" },
];

export default function Dashboard() {
  const { user } = useAuth();
  const [summary, setSummary] = useState(null);
  const [events, setEvents] = useState([]);
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    Promise.allSettled([
      api.get("/reports/summary"),
      api.get("/audit", { params: { limit: 8, offset: 0 } }),
    ]).then((results) => {
      if (!active) return;
      const nextErrors = {};
      if (results[0].status === "fulfilled") setSummary(results[0].value.data);
      else nextErrors.summary = getErrorMessage(results[0].reason);
      if (results[1].status === "fulfilled") setEvents(results[1].value.data);
      else nextErrors.audit = getErrorMessage(results[1].reason);
      setErrors(nextErrors);
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  return (
    <>
      <PageHeader eyebrow="Overview" title={`Good day${user?.display_name ? `, ${user.display_name.split(" ")[0]}` : ""}`} description="A current view of credential activity and recent system events." />
      {loading ? <LoadingState label="Loading live dashboard data…" /> : (
        <>
          {errors.summary && <Notice>{errors.summary}</Notice>}
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {cards.map(({ key, label, icon: Icon, tone }) => (
              <Card key={key} className="flex items-start justify-between">
                <div><p className="text-sm text-muted">{label}</p><p className="mt-3 text-3xl font-semibold tracking-tight text-ink">{summary ? (key === "active" ? summary.credentials_by_status?.active ?? 0 : summary[key] ?? 0).toLocaleString() : "—"}</p></div>
                <span className={`grid size-11 place-items-center rounded-xl ${tone === "lavender" ? "bg-lavender-100 text-lavender-800" : tone === "sand" ? "bg-amber-50 text-amber-800" : "bg-sage-100 text-sage-900"}`}><Icon size={20} /></span>
              </Card>
            ))}
          </div>
          <div className="mt-5 grid gap-5 xl:grid-cols-[1.5fr_.8fr]">
            <Card>
              <div className="mb-4 flex items-center justify-between"><div><h2 className="font-semibold text-ink">Recent audit activity</h2><p className="mt-1 text-xs text-muted">Latest recorded lifecycle events</p></div><Activity size={18} className="text-sage-800" /></div>
              {errors.audit ? <Notice>{errors.audit}</Notice> : <DataTable empty="No audit events have been recorded." columns={[
                { key: "event_type", label: "Event" },
                { key: "target_reference", label: "Record" },
                { key: "actor_reference", label: "Actor" },
                { key: "occurred_at", label: "Time", render: (row) => row.occurred_at ? new Date(row.occurred_at).toLocaleString() : "—" },
              ]} rows={events} />}
            </Card>
            <Card className="bg-[#f7f6f1]">
              <div className="grid size-10 place-items-center rounded-xl bg-white text-sage-800"><Users size={20} /></div>
              <h2 className="mt-5 font-semibold text-ink">Academic records</h2>
              <p className="mt-2 text-sm leading-6 text-muted">The API does not expose aggregate learner or course totals yet. Open the directories to browse the available records.</p>
              <div className="mt-5 flex flex-wrap gap-2">
                <Link to="/learners" className="inline-flex items-center gap-2 rounded-xl border border-line bg-white px-3 py-2 text-sm font-medium text-ink hover:border-sage-300"><Users size={15} />Learners</Link>
                <Link to="/courses" className="inline-flex items-center gap-2 rounded-xl border border-line bg-white px-3 py-2 text-sm font-medium text-ink hover:border-sage-300"><BookOpen size={15} />Courses</Link>
              </div>
            </Card>
          </div>
        </>
      )}
    </>
  );
}
