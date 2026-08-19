import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { api } from "../lib/api";
import type { UsageSummary } from "../lib/types";

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-surface-raised p-5">
      <div className="text-2xl font-semibold text-slate-100">{value}</div>
      <div className="mt-1 text-xs uppercase tracking-wide text-slate-500">{label}</div>
    </div>
  );
}

export function UsagePage() {
  const { data } = useQuery({ queryKey: ["usage"], queryFn: () => api<UsageSummary>("/api/usage") });

  return (
    <div className="min-h-screen bg-black">
      <div className="mx-auto max-w-3xl px-4 py-8">
        <Link to="/" className="mb-6 inline-flex items-center gap-2 text-sm text-slate-400 hover:text-slate-100">
          <ArrowLeft size={16} /> Back to chat
        </Link>
        <h1 className="mb-6 text-2xl font-semibold text-slate-100">Usage</h1>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Stat label="Requests" value={data?.total_requests ?? 0} />
          <Stat label="Successful" value={data?.successful_requests ?? 0} />
          <Stat label="Failed" value={data?.failed_requests ?? 0} />
          <Stat label="Tokens" value={(data?.total_tokens ?? 0).toLocaleString()} />
        </div>
        <p className="mt-2 text-xs text-slate-600">
          Token totals only include counts actually reported by NVIDIA; unknown values are omitted.
        </p>

        <h2 className="mb-3 mt-8 text-sm font-semibold uppercase tracking-wide text-slate-400">Recent activity</h2>
        <div className="overflow-hidden rounded-2xl border border-white/10">
          <table className="w-full text-sm">
            <thead className="bg-surface-raised text-left text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-2">Model</th>
                <th className="px-4 py-2">Endpoint</th>
                <th className="px-4 py-2">Status</th>
                <th className="px-4 py-2">Latency</th>
                <th className="px-4 py-2">Tokens</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {(data?.recent ?? []).map((r, i) => (
                <tr key={i} className="bg-black/20">
                  <td className="px-4 py-2 font-mono text-xs text-slate-300">{r.model_id ?? "—"}</td>
                  <td className="px-4 py-2 text-slate-400">{r.endpoint}</td>
                  <td className="px-4 py-2">
                    <span className={r.success ? "text-nv-green" : "text-red-400"}>
                      {r.success ? "ok" : "error"}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-slate-400">{r.latency_ms != null ? `${r.latency_ms} ms` : "—"}</td>
                  <td className="px-4 py-2 text-slate-400">{r.total_tokens ?? "—"}</td>
                </tr>
              ))}
              {(!data || data.recent.length === 0) && (
                <tr>
                  <td colSpan={5} className="px-4 py-6 text-center text-slate-500">No activity yet.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
