import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api } from "../lib/api";
import type { User } from "../lib/types";

interface AuthState {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  async function refresh() {
    try {
      const me = await api<User>("/api/auth/me");
      setUser(me);
    } catch {
      setUser(null);
    }
  }

  useEffect(() => {
    refresh().finally(() => setLoading(false));
  }, []);

  async function login(email: string, password: string) {
    const u = await api<User>("/api/auth/login", { method: "POST", body: { email, password } });
    setUser(u);
  }

  async function register(email: string, password: string) {
    const u = await api<User>("/api/auth/register", { method: "POST", body: { email, password } });
    setUser(u);
  }

  async function logout() {
    try {
      await api("/api/auth/logout", { method: "POST" });
    } finally {
      setUser(null);
    }
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, refresh }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
