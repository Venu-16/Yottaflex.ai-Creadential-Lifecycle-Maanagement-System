import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import api, { TOKEN_KEY } from "../services/api.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(Boolean(window.localStorage.getItem(TOKEN_KEY)));

  const logout = useCallback(() => {
    window.localStorage.removeItem(TOKEN_KEY);
    setUser(null);
    setLoading(false);
  }, []);

  useEffect(() => {
    const handleUnauthorized = () => {
      setUser(null);
      setLoading(false);
    };
    window.addEventListener("credential:unauthorized", handleUnauthorized);
    return () => window.removeEventListener("credential:unauthorized", handleUnauthorized);
  }, []);

  useEffect(() => {
    if (!window.localStorage.getItem(TOKEN_KEY)) return;
    let active = true;
    api.get("/auth/me")
      .then(({ data }) => { if (active) setUser(data); })
      .catch(() => { if (active) logout(); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [logout]);

  const login = useCallback(async (principal_key, password) => {
    const { data } = await api.post("/auth/login", { principal_key, password });
    window.localStorage.setItem(TOKEN_KEY, data.access_token);
    try {
      const profile = await api.get("/auth/me");
      setUser(profile.data);
      return profile.data;
    } catch (error) {
      logout();
      throw error;
    }
  }, [logout]);

  const value = useMemo(() => ({ user, loading, login, logout }), [user, loading, login, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}
