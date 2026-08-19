import { Link } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { toast } from "sonner";
import { api, ApiError } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import type { Model } from "../lib/types";

interface Stats {
  total_users: number;
  active_users: number;
  total_requests: number;
  total_errors: number;
  model_usage: Array<{ model_id: string | null; requests: number }>;
  database_ok: boolean;
  maintenance_mode: boolean;
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-surface-raised p-5">
      <div className="text-2xl font-semibold text-slate-100">{value}</div>
      <div className="mt-1 text-xs uppercase tracking-wide text-slate-500">{label}</div>
    </div>
  );
}

export function AdminPage() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const { data: stats } = useQuery({ queryKey: ["admin-stats"], queryFn: () => api<Stats>("/api/admin/stats") });
  const { data: models = [] } = useQuery({ queryKey: ["admin-models"], queryFn: () => api<Model[]>("/api/admin/models") });

  if (user?.role !== "admin") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-black text-slate-400">
        Admin access required.
      </div>
    );
  }

  const toggleModel = async (m: Model) => {
    try {
      await api(`/api/admin/models/${m.id}`, { method: "PATCH", body: { enabled: !m.enabled } });
      qc.invalidateQueries({ queryKey: ["admin-models"] });
      qc.invalidateQueries({ queryKey: ["models"] });
    } catch (err) {
      toast.error(err instanceof ApiError ? err.detail : "Failed to update model");
    }
  };

  const toggleMaintenance = async () => {
    try {
      await api(`/api/admin/maintenance?enabled=${!stats?.maintenance_mode}`, { method: "POST" });
      qc.invalidateQueries({ queryKey: ["admin-stats"] });
    } catch (err) {
      toast.error(err instanceof ApiError ? err.detail : "Failed to toggle maintenance");
    }
  };

  return (
    <div className="min-h-screen bg-black">
      <div className="mx-auto max-w-3xl px-4 py-8">
        <Link to="/" className="mb-6 inline-flex items-center gap-2 text-sm text-slate-400 hover:text-slate-100">
          <ArrowLeft size={16} /> Back to chat
        </Link>
        <h1 className="mb-6 text-2xl font-semibold text-slate-100">Admin</h1>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Stat label="Users" value={stats?.total_users ?? 0} />
          <Stat label="Active" value={stats?.active_users ?? 0} />
          <Stat label="Requests" value={stats?.total_requests ?? 0} />
          <Stat label="Errors" value={stats?.total_errors ?? 0} />
        </div>

        <div className="mt-4 flex items-center justify-between rounded-2xl border border-white/10 bg-surface-raised p-5">
          <div>
            <div className="text-sm font-medium text-slate-100">System status</div>
            <div className="mt-1 text-xs text-slate-500">
              Database: <span className={stats?.database_ok ? "text-nv-green" : "text-red-400"}>
                {stats?.database_ok ? "healthy" : "unavailable"}
              </span>
            </div>
          </div>
          <button
            onClick={toggleMaintenance}
            className={`rounded-lg px-4 py-2 text-sm font-medium ${
              stats?.maintenance_mode ? "bg-red-500/20 text-red-300" : "bg-surface-muted text-slate-300"
            }`}
          >
            {stats?.maintenance_mode ? "Maintenance ON" : "Maintenance OFF"}
          </button>
        </div>

        <h2 className="mb-3 mt-8 text-sm font-semibold uppercase tracking-wide text-slate-400">Models</h2>
        <div className="space-y-2">
          {models.map((m) => (
            <div key={m.id} className="flex items-center justify-between rounded-xl border border-white/10 bg-surface-raised px-4 py-3">
              <div className="min-w-0">
                <div className="truncate text-sm font-medium text-slate-100">{m.display_name}</div>
                <div className="truncate font-mono text-[11px] text-slate-500">{m.id}</div>
              </div>
              <button
                onClick={() => toggleModel(m)}
                className={`relative h-6 w-11 shrink-0 rounded-full transition ${m.enabled ? "bg-nv-green" : "bg-surface-muted"}`}
              >
                <span className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition ${m.enabled ? "left-[22px]" : "left-0.5"}`} />
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
