import { useState } from "react";
import { BadgeCheck, SearchCheck, ShieldAlert } from "lucide-react";
import { Card, Field, Button, Notice, PageHeader, StatusPill } from "../../components/common/ui.jsx";
import api, { getErrorMessage } from "../../services/api.js";

export default function Verification() {
  const [credentialId, setCredentialId] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function verify(event) {
    event.preventDefault();
    setError("");
    setResult(null);
    setLoading(true);
    try {
      const { data } = await api.post("/verification/credential-id", null, { params: { credential_id: credentialId.trim() } });
      setResult(data);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <PageHeader eyebrow="Public lookup" title="Verify a credential" description="Check an issued credential against the authoritative registry. Results show verification status only and do not reveal learner profile details." />
      <div className="grid gap-5 lg:grid-cols-[.9fr_1.1fr]">
        <Card>
          <div className="mb-4 grid size-11 place-items-center rounded-xl bg-lavender-100 text-lavender-800"><SearchCheck size={21} /></div>
          <h2 className="font-semibold text-ink">Credential ID lookup</h2>
          <p className="mt-1 text-sm leading-6 text-muted">Enter the credential identifier exactly as it appears on the document.</p>
          <form onSubmit={verify} className="mt-5 space-y-4">
            <Field label="Credential ID" value={credentialId} onChange={(event) => setCredentialId(event.target.value)} required maxLength={15} placeholder="CRD-00000001" />
            {error && <Notice>{error}</Notice>}
            <Button disabled={loading || !credentialId.trim()}>{loading ? "Checking registry…" : "Verify credential"}</Button>
          </form>
        </Card>
        <Card className="min-h-64">
          {!result ? (
            <div className="flex h-full min-h-56 flex-col items-center justify-center text-center">
              <span className="grid size-12 place-items-center rounded-2xl bg-ivory text-muted"><ShieldAlert size={23} /></span>
              <p className="mt-4 font-medium text-ink">Verification result</p>
              <p className="mt-1 max-w-sm text-sm leading-6 text-muted">Submit an identifier to see registry, integrity, issuer trust, and lifecycle results.</p>
            </div>
          ) : (
            <div>
              <div className="flex items-start gap-3">
                <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-sage-100 text-sage-900"><BadgeCheck size={22} /></span>
                <div><p className="text-xs font-bold uppercase tracking-wider text-muted">Verification result</p><div className="mt-2 flex flex-wrap gap-2"><StatusPill value={result.overall_result} /><StatusPill value={result.lifecycle_result} /></div></div>
              </div>
              <p className="mt-5 rounded-xl bg-ivory p-4 text-sm leading-6 text-ink">{result.message}</p>
              <dl className="mt-5 grid gap-4 sm:grid-cols-2">
                {[
                  ["Credential ID", result.credential_id],
                  ["Issuer", result.issuer_code],
                  ["Integrity", result.integrity_result],
                  ["Issuer trust", result.issuer_trust_result],
                  ["Lifecycle", result.lifecycle_result],
                ].map(([label, value]) => <div key={label}><dt className="text-xs font-medium text-muted">{label}</dt><dd className="mt-1 break-all text-sm font-medium text-ink">{value || "—"}</dd></div>)}
              </dl>
            </div>
          )}
        </Card>
      </div>
    </>
  );
}
