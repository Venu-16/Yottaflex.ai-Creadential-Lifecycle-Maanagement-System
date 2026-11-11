import { useState } from "react";
import { ArrowRight, Award, ShieldCheck } from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext.jsx";
import { getErrorMessage } from "../../services/api.js";
import { Button, Field, Notice } from "../../components/common/ui.jsx";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [principalKey, setPrincipalKey] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await login(principalKey, password);
      navigate(location.state?.from?.pathname || "/", { replace: true });
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="grid min-h-screen bg-ivory lg:grid-cols-[1.05fr_.95fr]">
      <section className="hidden flex-col justify-between bg-sage-900 p-12 text-white lg:flex">
        <div className="flex items-center gap-3"><span className="grid size-11 place-items-center rounded-2xl bg-white/10"><Award size={23} /></span><span className="font-semibold tracking-tight">Meridian Credentials</span></div>
        <div className="max-w-xl pb-16">
          <p className="mb-5 text-xs font-bold uppercase tracking-[0.2em] text-sage-200">Academic credential management</p>
          <h1 className="text-5xl font-semibold leading-tight tracking-tight">Achievements, made verifiable.</h1>
          <p className="mt-6 max-w-lg text-base leading-7 text-sage-100/80">Manage learning records, evaluate eligibility, and issue credentials with integrity built into every step.</p>
        </div>
        <p className="text-xs text-sage-100/70">A secure workspace for trusted learning outcomes.</p>
      </section>
      <section className="flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-md">
          <div className="mb-9 flex items-center gap-3 lg:hidden"><span className="grid size-10 place-items-center rounded-xl bg-sage-800 text-white"><Award size={21} /></span><span className="font-semibold text-ink">Meridian Credentials</span></div>
          <div className="mb-8">
            <div className="mb-5 grid size-12 place-items-center rounded-2xl bg-lavender-100 text-lavender-800"><ShieldCheck size={24} /></div>
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-sage-700">Welcome back</p>
            <h2 className="mt-2 text-3xl font-semibold tracking-tight text-ink">Sign in to your workspace</h2>
            <p className="mt-2 text-sm leading-6 text-muted">Use the account provisioned for your institution.</p>
          </div>
          <form onSubmit={submit} className="space-y-5">
            {error && <Notice>{error}</Notice>}
            <Field label="Account identifier" autoComplete="username" value={principalKey} onChange={(event) => setPrincipalKey(event.target.value)} required maxLength={200} />
            <Field label="Password" type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required maxLength={1024} />
            <Button className="w-full" disabled={submitting}>{submitting ? "Signing in…" : "Sign in"} {!submitting && <ArrowRight size={16} />}</Button>
          </form>
          <p className="mt-7 text-center text-xs leading-5 text-muted">Access is managed by your institution. Public credential checks are available without signing in.</p>
        </div>
      </section>
    </main>
  );
}
