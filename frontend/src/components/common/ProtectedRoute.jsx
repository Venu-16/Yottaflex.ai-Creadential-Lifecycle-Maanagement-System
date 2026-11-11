import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../../context/AuthContext.jsx";
import { LoadingState } from "./ui.jsx";

export default function ProtectedRoute({ roles }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <div className="grid min-h-screen place-items-center"><LoadingState label="Restoring your session…" /></div>;
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />;
  if (roles && !user.roles?.some((role) => roles.includes(role))) return <Navigate to="/verification" replace />;
  return <Outlet />;
}
