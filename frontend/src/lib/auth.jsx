import { createContext, useContext, useEffect, useState, useCallback } from "react";
import api from "./api";

const AuthCtx = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null); // null=loading, false=guest, obj=user
  const [ready, setReady] = useState(false);

  const bootstrap = useCallback(async () => {
    const token = localStorage.getItem("pest_token");
    if (!token) { setUser(false); setReady(true); return; }
    try {
      const { data } = await api.get("/auth/me");
      setUser(data);
    } catch {
      localStorage.removeItem("pest_token");
      setUser(false);
    } finally { setReady(true); }
  }, []);

  useEffect(() => { bootstrap(); }, [bootstrap]);

  const login = async (email, password) => {
    const { data } = await api.post("/auth/login", { email, password });
    localStorage.setItem("pest_token", data.token);
    setUser(data.user);
    return data.user;
  };

  const logout = async () => {
    try { await api.post("/auth/logout"); } catch {}
    localStorage.removeItem("pest_token");
    setUser(false);
  };

  const refresh = async () => {
    const { data } = await api.get("/auth/me");
    setUser(data);
  };

  const can = (module, action) => {
    if (!user) return false;
    if (user.role === "admin") return true;
    return !!user.permissions?.[module]?.[action];
  };

  return (
    <AuthCtx.Provider value={{ user, ready, login, logout, refresh, can }}>
      {children}
    </AuthCtx.Provider>
  );
}

export const useAuth = () => useContext(AuthCtx);
