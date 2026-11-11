import { useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  Activity, Award, BookOpen, CheckCircle2, ChevronRight, ClipboardList,
  FileCheck2, FileText, GraduationCap, LayoutDashboard, LogOut, Menu, SearchCheck, Users, X,
} from "lucide-react";
import { useAuth } from "../../context/AuthContext.jsx";

const academicRoles = ["PLATFORM_ADMINISTRATOR", "ACADEMIC_ADMINISTRATOR"];
const navigation = [
  { to: "/", label: "Overview", icon: LayoutDashboard, roles: academicRoles },
  { to: "/learners", label: "Learners", icon: Users, roles: academicRoles },
  { to: "/courses", label: "Courses", icon: BookOpen, roles: academicRoles },
  { to: "/rules", label: "Credential rules", icon: ClipboardList, roles: academicRoles },
  { to: "/completions", label: "Learning records", icon: GraduationCap, roles: academicRoles },
  { to: "/eligibility", label: "Eligibility", icon: CheckCircle2, roles: academicRoles },
  { to: "/credentials", label: "Credentials", icon: Award, roles: ["PLATFORM_ADMINISTRATOR", "ACADEMIC_ADMINISTRATOR", "LEARNER"] },
  { to: "/revocations", label: "Revocations", icon: FileCheck2, roles: ["ACADEMIC_ADMINISTRATOR"] },
  { to: "/audit", label: "Audit history", icon: Activity, roles: academicRoles },
  { to: "/reports", label: "Reports", icon: FileText, roles: academicRoles },
  { to: "/analytics", label: "Data & analytics", icon: Activity, roles: academicRoles },
];

export default function AppLayout() {
  const { user, logout } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const roleNames = (user?.roles || []).map((role) => role.replaceAll("_", " ").toLowerCase()).join(", ");
  const links = navigation.filter((item) => user?.roles?.some((role) => item.roles.includes(role)));
  const title = navigation.find((item) => item.to === location.pathname)?.label || (location.pathname === "/verification" ? "Credential verification" : "Workspace");

  function signOut() {
    logout();
    navigate("/login", { replace: true });
  }

  const sidebar = (
    <div className="flex h-full flex-col">
      <div className="flex h-[76px] items-center gap-3 border-b border-white/10 px-5">
        <span className="grid size-10 place-items-center rounded-xl bg-sage-700 text-white"><Award size={21} /></span>
        <div><p className="font-semibold tracking-tight text-white">Meridian</p><p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-sage-200">Credentials</p></div>
        <button className="ml-auto rounded-lg p-2 text-sage-100 hover:bg-white/10 lg:hidden" onClick={() => setMobileOpen(false)} aria-label="Close navigation"><X size={18} /></button>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto px-4 pt-6">
        <p className="mb-3 px-3 text-[10px] font-bold uppercase tracking-[0.18em] text-sage-300">Workspace</p>
        <nav className="space-y-1">
          {links.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} end={to === "/"} onClick={() => setMobileOpen(false)} className={({ isActive }) => `flex items-center gap-3 rounded-xl px-3 py-2.5 text-[13px] font-medium transition ${isActive ? "bg-white text-sage-900 shadow-sm" : "text-sage-100/85 hover:bg-white/10 hover:text-white"}`}>
              <Icon size={17} strokeWidth={1.8} /><span>{label}</span>{location.pathname === to && <ChevronRight className="ml-auto" size={15} />}
            </NavLink>
          ))}
          <NavLink to="/verification" onClick={() => setMobileOpen(false)} className={({ isActive }) => `flex items-center gap-3 rounded-xl px-3 py-2.5 text-[13px] font-medium transition ${isActive ? "bg-white text-sage-900 shadow-sm" : "text-sage-100/85 hover:bg-white/10 hover:text-white"}`}>
            <SearchCheck size={17} strokeWidth={1.8} /><span>Public verification</span>
          </NavLink>
        </nav>
      </div>
      <div className="mt-auto p-4">
        <div className="rounded-2xl border border-white/10 bg-white/5 p-3">
          <div className="flex items-center gap-3">
            <span className="grid size-9 shrink-0 place-items-center rounded-full bg-lavender-200 text-xs font-bold uppercase text-lavender-900">{(user?.display_name || user?.principal_key || "U").slice(0, 1)}</span>
            <div className="min-w-0"><p className="truncate text-sm font-medium text-white">{user?.display_name || user?.principal_key}</p><p className="mt-0.5 truncate text-[10px] capitalize text-sage-200">{roleNames || "No active role"}</p></div>
          </div>
          <button onClick={signOut} className="mt-3 flex w-full items-center gap-2 rounded-lg px-2 py-2 text-xs font-medium text-sage-100 hover:bg-white/10"><LogOut size={15} />Sign out</button>
        </div>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-ivory text-ink">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-[258px] bg-sage-950 lg:block">{sidebar}</aside>
      {mobileOpen && <div className="fixed inset-0 z-40 lg:hidden"><button aria-label="Close navigation overlay" className="absolute inset-0 bg-sage-950/40" onClick={() => setMobileOpen(false)} /><aside className="absolute inset-y-0 left-0 w-[280px] bg-sage-950 shadow-xl">{sidebar}</aside></div>}
      <div className="lg:pl-[258px]">
        <header className="sticky top-0 z-20 flex h-[76px] items-center justify-between border-b border-line bg-white/95 px-4 backdrop-blur sm:px-7">
          <div className="flex items-center gap-3">
            <button className="rounded-lg p-2 text-muted hover:bg-ivory lg:hidden" onClick={() => setMobileOpen(true)} aria-label="Open navigation"><Menu size={20} /></button>
            <div><p className="text-xs text-muted">Credential management</p><p className="mt-0.5 text-sm font-semibold text-ink">{title}</p></div>
          </div>
          <div className="flex items-center gap-3">
            <span className="hidden items-center gap-2 rounded-full bg-sage-50 px-3 py-1.5 text-xs font-medium text-sage-900 sm:inline-flex"><span className="size-1.5 rounded-full bg-sage-600" />API workspace</span>
            <span className="grid size-9 place-items-center rounded-full bg-lavender-100 text-xs font-bold uppercase text-lavender-900">{(user?.display_name || user?.principal_key || "U").slice(0, 1)}</span>
          </div>
        </header>
        <main className="mx-auto max-w-[1440px] px-4 py-7 sm:px-7 lg:px-9"><Outlet /></main>
        <footer className="border-t border-line px-7 py-4 text-center text-xs text-muted">Credential Lifecycle Management · Academic operations</footer>
      </div>
    </div>
  );
}
