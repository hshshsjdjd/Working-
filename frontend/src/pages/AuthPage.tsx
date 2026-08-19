import { useState } from "react";
import { toast } from "sonner";
import { useAuth } from "../context/AuthContext";
import { ApiError } from "../lib/api";

export function AuthPage() {
  const { login, register } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      if (mode === "login") await login(email, password);
      else await register(email, password);
      toast.success(mode === "login" ? "Welcome back" : "Account created");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.detail : "Something went wrong");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-black px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-2xl bg-nv-green text-2xl font-bold text-black">
            N
          </div>
          <h1 className="text-2xl font-semibold text-slate-100">NVIDIA AI</h1>
          <p className="mt-1 text-sm text-slate-500">
            {mode === "login" ? "Sign in to continue" : "Create your account"}
          </p>
        </div>

        <form onSubmit={submit} className="space-y-3 rounded-2xl border border-white/10 bg-surface-raised p-6">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-400">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              className="w-full rounded-lg border border-white/10 bg-black/40 px-3 py-2.5 text-slate-100 focus:border-nv-green/60 focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-400">Password</label>
            <input
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              className="w-full rounded-lg border border-white/10 bg-black/40 px-3 py-2.5 text-slate-100 focus:border-nv-green/60 focus:outline-none"
            />
            {mode === "register" && (
              <p className="mt-1 text-[11px] text-slate-500">At least 8 characters.</p>
            )}
          </div>
          <button
            type="submit"
            disabled={busy}
            className="w-full rounded-lg bg-nv-green py-2.5 font-semibold text-black transition hover:bg-nv-greenDark disabled:opacity-50"
          >
            {busy ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}
          </button>
        </form>

        <p className="mt-4 text-center text-sm text-slate-500">
          {mode === "login" ? "New here?" : "Already have an account?"}{" "}
          <button
            onClick={() => setMode(mode === "login" ? "register" : "login")}
            className="font-medium text-nv-green hover:underline"
          >
            {mode === "login" ? "Create an account" : "Sign in"}
          </button>
        </p>
      </div>
    </div>
  );
}
