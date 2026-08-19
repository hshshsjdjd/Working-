import { useEffect, useRef, useState } from "react";
import { Paperclip, Send, Square, X } from "lucide-react";
import { toast } from "sonner";
import { api, ApiError } from "../lib/api";
import type { UploadedFile } from "../lib/types";

interface Props {
  conversationId: string | null;
  streaming: boolean;
  prefill?: string;
  onSend: (content: string, fileIds: string[]) => void;
  onStop: () => void;
}

const ACCEPT = ".txt,.md,.csv,.json,text/plain,text/markdown,text/csv,application/json";

export function Composer({ conversationId, streaming, prefill, onSend, onStop }: Props) {
  const [value, setValue] = useState("");
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [uploading, setUploading] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (prefill !== undefined) {
      setValue(prefill);
      textareaRef.current?.focus();
    }
  }, [prefill]);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, [value]);

  const submit = () => {
    const trimmed = value.trim();
    if (!trimmed || streaming) return;
    onSend(trimmed, files.map((f) => f.id));
    setValue("");
    setFiles([]);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      if (conversationId) fd.append("conversation_id", conversationId);
      const uploaded = await api<UploadedFile>("/api/files", { method: "POST", body: fd });
      setFiles((prev) => [...prev, uploaded]);
      toast.success(`Attached ${uploaded.original_name}`);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.detail : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="border-t border-white/10 bg-black/40 px-3 py-3 backdrop-blur sm:px-6">
      <div className="mx-auto max-w-3xl">
        {files.length > 0 && (
          <div className="mb-2 flex flex-wrap gap-2">
            {files.map((f) => (
              <span
                key={f.id}
                className="flex items-center gap-1 rounded-full bg-surface-muted px-2.5 py-1 text-xs text-slate-300"
              >
                {f.original_name}
                <button onClick={() => setFiles((p) => p.filter((x) => x.id !== f.id))}>
                  <X size={12} />
                </button>
              </span>
            ))}
          </div>
        )}
        <div className="flex items-end gap-2 rounded-2xl border border-white/10 bg-surface-raised p-2 focus-within:border-nv-green/50">
          <input
            ref={fileInputRef}
            type="file"
            accept={ACCEPT}
            className="hidden"
            onChange={handleUpload}
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            title="Attach a text file"
            className="rounded-lg p-2 text-slate-400 transition hover:bg-white/10 hover:text-slate-100 disabled:opacity-50"
          >
            <Paperclip size={18} />
          </button>
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
            placeholder="Message NVIDIA AI…"
            className="max-h-[200px] flex-1 resize-none bg-transparent py-2 text-[15px] text-slate-100 placeholder:text-slate-500 focus:outline-none"
          />
          {streaming ? (
            <button
              onClick={onStop}
              className="flex items-center gap-1.5 rounded-xl bg-white/10 px-3 py-2 text-sm font-medium text-slate-100 hover:bg-white/20"
            >
              <Square size={15} className="fill-current" /> Stop
            </button>
          ) : (
            <button
              onClick={submit}
              disabled={!value.trim()}
              className="rounded-xl bg-nv-green p-2.5 text-black transition hover:bg-nv-greenDark disabled:cursor-not-allowed disabled:opacity-40"
              aria-label="Send message"
            >
              <Send size={18} />
            </button>
          )}
        </div>
        <p className="mt-1.5 text-center text-[11px] text-slate-600">
          AI responses may be inaccurate. Attachments support text files (.txt, .md, .csv, .json).
        </p>
      </div>
    </div>
  );
}
