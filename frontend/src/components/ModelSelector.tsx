import { useEffect, useRef, useState } from "react";
import { Check, ChevronDown, Eye, Sparkles } from "lucide-react";
import type { Model } from "../lib/types";

interface Props {
  models: Model[];
  value: string | null;
  onChange: (id: string) => void;
}

export function ModelSelector({ models, value, onChange }: Props) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const selected = models.find((m) => m.id === value) || models[0];

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex max-w-[60vw] items-center gap-1.5 rounded-lg border border-white/10 bg-surface-raised px-3 py-1.5 text-sm font-medium text-slate-100 hover:bg-surface-muted"
      >
        <Sparkles size={14} className="text-nv-green" />
        <span className="truncate">{selected ? selected.display_name : "Select model"}</span>
        <ChevronDown size={14} className="text-slate-400" />
      </button>

      {open && (
        <div className="absolute z-30 mt-2 w-80 max-w-[90vw] overflow-hidden rounded-xl border border-white/10 bg-surface-raised shadow-2xl">
          <div className="max-h-[60vh] overflow-y-auto py-1">
            {models.map((m) => (
              <button
                key={m.id}
                onClick={() => {
                  onChange(m.id);
                  setOpen(false);
                }}
                className="flex w-full items-start gap-2 px-3 py-2.5 text-left hover:bg-surface-muted"
              >
                <div className="mt-0.5 w-4 shrink-0">
                  {m.id === selected?.id && <Check size={15} className="text-nv-green" />}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="truncate text-sm font-medium text-slate-100">
                      {m.display_name}
                    </span>
                    {m.supports_vision && (
                      <span className="flex items-center gap-0.5 rounded bg-nv-green/15 px-1 py-0.5 text-[10px] text-nv-green">
                        <Eye size={10} /> vision
                      </span>
                    )}
                  </div>
                  <div className="truncate font-mono text-[11px] text-slate-500">{m.id}</div>
                  <div className="mt-0.5 line-clamp-2 text-xs text-slate-400">{m.description}</div>
                  <div className="mt-1 text-[10px] text-slate-500">
                    Context: {m.context_window.toLocaleString()} tokens
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
