import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { toast } from "sonner";
import { api, ApiError } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { useTheme, type Theme } from "../context/ThemeContext";
import type { Model, Settings } from "../lib/types";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-2xl border border-white/10 bg-surface-raised p-5">
      <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-400">{title}</h2>
      <div className="space-y-4">{children}</div>
    </section>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
      <span className="text-sm text-slate-300">{label}</span>
      <div className="sm:w-2/3 sm:max-w-xs">{children}</div>
    </div>
  );
}

export function SettingsPage() {
  const { user, logout } = useAuth();
  const { setTheme } = useTheme();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const { data: models = [] } = useQuery({ queryKey: ["models"], queryFn: () => api<Model[]>("/api/models") });
  const { data: settings } = useQuery({ queryKey: ["settings"], queryFn: () => api<Settings>("/api/settings") });
  const [form, setForm] = useState<Settings | null>(null);

  useEffect(() => {
    if (settings) setForm(settings);
  }, [settings]);

  const save = async (patch: Partial<Settings>) => {
    setForm((f) => (f ? { ...f, ...patch } : f));
    try {
      const updated = await api<Settings>("/api/settings", { method: "PATCH", body: patch });
      qc.setQueryData(["settings"], updated);
      if (patch.theme) setTheme(patch.theme as Theme);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.detail : "Could not save settings");
    }
  };

  const [curPw, setCurPw] = useState("");
  const [newPw, setNewPw] = useState("");

  const changePassword = async () => {
    try {
      await api("/api/auth/change-password", {
        method: "POST",
        body: { current_password: curPw, new_password: newPw },
      });
      toast.success("Password updated");
      setCurPw("");
      setNewPw("");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.detail : "Could not change password");
    }
  };

  const deleteAccount = async () => {
    const pw = window.prompt("Confirm your password to permanently delete your account:");
    if (!pw) return;
    try {
      await api("/api/auth/delete-account", { method: "POST", body: { password: pw } });
      toast.success("Account deleted");
      await logout();
      navigate("/");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.detail : "Could not delete account");
    }
  };

  if (!form) return null;
  const inputClass =
    "w-full rounded-lg border border-white/10 bg-black/40 px-3 py-2 text-sm text-slate-100 focus:border-nv-green/60 focus:outline-none";

  return (
    <div className="min-h-screen bg-black">
      <div className="mx-auto max-w-2xl px-4 py-8">
        <Link to="/" className="mb-6 inline-flex items-center gap-2 text-sm text-slate-400 hover:text-slate-100">
          <ArrowLeft size={16} /> Back to chat
        </Link>
        <h1 className="mb-6 text-2xl font-semibold text-slate-100">Settings</h1>
        <div className="space-y-5">
          <Section title="Appearance">
            <Row label="Theme">
              <select className={inputClass} value={form.theme} onChange={(e) => save({ theme: e.target.value as Theme })}>
                <option value="amoled">AMOLED (pure black)</option>
                <option value="dark">Dark</option>
                <option value="light">Light</option>
                <option value="system">System</option>
              </select>
            </Row>
          </Section>

          <Section title="AI">
            <Row label="Default model">
              <select
                className={inputClass}
                value={form.default_model_id ?? ""}
                onChange={(e) => save({ default_model_id: e.target.value })}
              >
                <option value="">Auto (first available)</option>
                {models.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.display_name}
                  </option>
                ))}
              </select>
            </Row>
            <Row label={`Temperature (${form.temperature.toFixed(2)})`}>
              <input type="range" min={0} max={2} step={0.05} value={form.temperature}
                onChange={(e) => setForm({ ...form, temperature: Number(e.target.value) })}
                onMouseUp={(e) => save({ temperature: Number((e.target as HTMLInputElement).value) })}
                onTouchEnd={(e) => save({ temperature: Number((e.target as HTMLInputElement).value) })}
                className="w-full accent-nv-green" />
            </Row>
            <Row label={`Top-p (${form.top_p.toFixed(2)})`}>
              <input type="range" min={0} max={1} step={0.05} value={form.top_p}
                onChange={(e) => setForm({ ...form, top_p: Number(e.target.value) })}
                onMouseUp={(e) => save({ top_p: Number((e.target as HTMLInputElement).value) })}
                onTouchEnd={(e) => save({ top_p: Number((e.target as HTMLInputElement).value) })}
                className="w-full accent-nv-green" />
            </Row>
            <Row label="Max tokens">
              <input type="number" min={1} max={32768} className={inputClass} value={form.max_tokens}
                onChange={(e) => setForm({ ...form, max_tokens: Number(e.target.value) })}
                onBlur={(e) => save({ max_tokens: Number(e.target.value) })} />
            </Row>
            <div>
              <span className="text-sm text-slate-300">Custom system prompt</span>
              <textarea rows={3} className={`${inputClass} mt-2`} value={form.system_prompt ?? ""}
                placeholder="e.g. You are a concise senior engineer."
                onChange={(e) => setForm({ ...form, system_prompt: e.target.value })}
                onBlur={(e) => save({ system_prompt: e.target.value })} />
            </div>
          </Section>

          <Section title="Chat">
            {(["streaming", "markdown", "code_highlight", "auto_scroll"] as const).map((key) => (
              <Row key={key} label={key.replace("_", " ")}>
                <button
                  onClick={() => save({ [key]: !form[key] } as Partial<Settings>)}
                  className={`relative h-6 w-11 rounded-full transition ${form[key] ? "bg-nv-green" : "bg-surface-muted"}`}
                >
                  <span className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition ${form[key] ? "left-[22px]" : "left-0.5"}`} />
                </button>
              </Row>
            ))}
          </Section>

          <Section title="Account">
            <Row label="Email"><span className="text-sm text-slate-400">{user?.email}</span></Row>
            <div className="space-y-2">
              <span className="text-sm text-slate-300">Change password</span>
              <input type="password" placeholder="Current password" className={inputClass} value={curPw} onChange={(e) => setCurPw(e.target.value)} />
              <input type="password" placeholder="New password (min 8 chars)" className={inputClass} value={newPw} onChange={(e) => setNewPw(e.target.value)} />
              <button onClick={changePassword} disabled={!curPw || newPw.length < 8}
                className="rounded-lg bg-nv-green px-4 py-2 text-sm font-semibold text-black hover:bg-nv-greenDark disabled:opacity-40">
                Update password
              </button>
            </div>
            <div className="border-t border-white/10 pt-4">
              <button onClick={deleteAccount} className="rounded-lg border border-red-500/40 px-4 py-2 text-sm font-medium text-red-400 hover:bg-red-500/10">
                Delete account
              </button>
            </div>
          </Section>
        </div>
      </div>
    </div>
  );
}
