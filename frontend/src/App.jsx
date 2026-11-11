import { Navigate, Route, Routes } from "react-router-dom";
import AppLayout from "./components/layout/AppLayout.jsx";
import ProtectedRoute from "./components/common/ProtectedRoute.jsx";
import { AuthProvider, useAuth } from "./context/AuthContext.jsx";
import Dashboard from "./pages/dashboard/Dashboard.jsx";
import Login from "./pages/auth/Login.jsx";
import Verification from "./pages/verification/Verification.jsx";
import Workspace from "./pages/Workspace.jsx";

const ACADEMIC = ["PLATFORM_ADMINISTRATOR", "ACADEMIC_ADMINISTRATOR"];
const CREDENTIAL_READERS = [...ACADEMIC, "LEARNER"];

function HomeRedirect() {
  const { user } = useAuth();
  if (user?.roles?.some((role) => ACADEMIC.includes(role))) return <Dashboard />;
  if (user?.roles?.includes("LEARNER")) return <Navigate to="/credentials" replace />;
  return <Navigate to="/verification" replace />;
}

function ApplicationRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<AppLayout />}>
        <Route path="/verification" element={<Verification />} />
      </Route>
      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route index element={<HomeRedirect />} />
          <Route element={<ProtectedRoute roles={ACADEMIC} />}>
            <Route path="learners" element={<Workspace page="learners" />} />
            <Route path="courses" element={<Workspace page="courses" />} />
            <Route path="rules" element={<Workspace page="rules" />} />
            <Route path="completions" element={<Workspace page="completions" />} />
            <Route path="eligibility" element={<Workspace page="eligibility" />} />
            <Route path="audit" element={<Workspace page="audit" />} />
            <Route path="reports" element={<Workspace page="reports" />} />
          </Route>
          <Route element={<ProtectedRoute roles={CREDENTIAL_READERS} />}>
            <Route path="credentials" element={<Workspace page="credentials" />} />
          </Route>
          <Route element={<ProtectedRoute roles={["ACADEMIC_ADMINISTRATOR"]} />}>
            <Route path="revocations" element={<Workspace page="revocations" />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return <AuthProvider><ApplicationRoutes /></AuthProvider>;
}
