import { useState } from "react";
import { Check, Copy, Pencil, RefreshCw, User as UserIcon } from "lucide-react";
import { Markdown } from "./Markdown";
import type { Message } from "../lib/types";

interface Props {
  message: Message;
  streaming?: boolean;
  isLastAssistant?: boolean;
  useMarkdown: boolean;
  onRegenerate?: () => void;
  onEdit?: (content: string) => void;
}

function timeLabel(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export function MessageItem({
  message,
  streaming,
  isLastAssistant,
  useMarkdown,
  onRegenerate,
  onEdit,
}: Props) {
  const [copied, setCopied] = useState(false);
  const isUser = message.role === "user";

  const copy = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="animate-fade-in group px-4 py-4 sm:px-6">
      <div className="mx-auto flex max-w-3xl gap-3">
        <div
          className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
            isUser ? "bg-surface-muted text-slate-300" : "bg-nv-green text-black"
          }`}
        >
          {isUser ? <UserIcon size={16} /> : "AI"}
        </div>
        <div className="min-w-0 flex-1">
          <div className="mb-1 flex items-center gap-2 text-xs text-slate-500">
            <span className="font-medium text-slate-400">{isUser ? "You" : "NVIDIA AI"}</span>
            <span>{timeLabel(message.created_at)}</span>
          </div>

          {isUser || !useMarkdown ? (
            <div className="whitespace-pre-wrap break-words text-[15px] leading-relaxed text-slate-100">
              {message.content}
            </div>
          ) : (
            <Markdown content={message.content} />
          )}

          {streaming && !message.content && (
            <span className="inline-block h-4 w-2 animate-blink bg-nv-green align-middle" />
          )}

          <div className="mt-2 flex items-center gap-1 opacity-0 transition group-hover:opacity-100">
            <button
              onClick={copy}
              className="flex items-center gap-1 rounded px-1.5 py-1 text-xs text-slate-400 hover:bg-white/10 hover:text-slate-100"
            >
              {copied ? <Check size={13} /> : <Copy size={13} />}
              {copied ? "Copied" : "Copy"}
            </button>
            {isUser && onEdit && (
              <button
                onClick={() => onEdit(message.content)}
                className="flex items-center gap-1 rounded px-1.5 py-1 text-xs text-slate-400 hover:bg-white/10 hover:text-slate-100"
              >
                <Pencil size={13} /> Edit
              </button>
            )}
            {!isUser && isLastAssistant && onRegenerate && !streaming && (
              <button
                onClick={onRegenerate}
                className="flex items-center gap-1 rounded px-1.5 py-1 text-xs text-slate-400 hover:bg-white/10 hover:text-slate-100"
              >
                <RefreshCw size={13} /> Regenerate
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
