import { useState } from "react";
import { Link } from "react-router-dom";
import {
  Archive,
  BarChart3,
  Check,
  LogOut,
  MessageSquarePlus,
  Pencil,
  Pin,
  PinOff,
  Search,
  Settings,
  Shield,
  Trash2,
  X,
} from "lucide-react";
import type { Conversation } from "../lib/types";

interface Props {
  conversations: Conversation[];
  activeId: string | null;
  userEmail: string;
  isAdmin: boolean;
  open: boolean;
  onClose: () => void;
  onNew: () => void;
  onSelect: (id: string) => void;
  onSearch: (q: string) => void;
  onRename: (id: string, title: string) => void;
  onDelete: (id: string) => void;
  onTogglePin: (c: Conversation) => void;
  onArchive: (c: Conversation) => void;
  onLogout: () => void;
}

export function Sidebar(props: Props) {
  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState("");

  const startEdit = (c: Conversation) => {
    setEditing(c.id);
    setDraft(c.title);
  };
  const commitEdit = (id: string) => {
    if (draft.trim()) props.onRename(id, draft.trim());
    setEditing(null);
  };

  return (
    <>
      {props.open && (
        <div className="fixed inset-0 z-30 bg-black/60 md:hidden" onClick={props.onClose} />
      )}
      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-72 flex-col border-r border-white/10 bg-surface-raised transition-transform md:static md:translate-x-0 ${
          props.open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between px-3 py-3">
          <div className="flex items-center gap-2 font-semibold">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-nv-green text-sm font-bold text-black">
              N
            </span>
            NVIDIA AI
          </div>
          <button className="rounded p-1 text-slate-400 hover:bg-white/10 md:hidden" onClick={props.onClose}>
            <X size={18} />
          </button>
        </div>

        <div className="px-3">
          <button
            onClick={props.onNew}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-nv-green py-2.5 text-sm font-semibold text-black transition hover:bg-nv-greenDark"
          >
            <MessageSquarePlus size={17} /> New chat
          </button>
        </div>

        <div className="px-3 py-3">
          <div className="flex items-center gap-2 rounded-lg bg-surface-muted px-2.5 py-1.5">
            <Search size={15} className="text-slate-500" />
            <input
              placeholder="Search chats"
              onChange={(e) => props.onSearch(e.target.value)}
              className="w-full bg-transparent text-sm text-slate-200 placeholder:text-slate-500 focus:outline-none"
            />
          </div>
        </div>

        <nav className="flex-1 space-y-0.5 overflow-y-auto px-2 pb-2">
          {props.conversations.length === 0 && (
            <p className="px-3 py-6 text-center text-sm text-slate-500">No conversations yet.</p>
          )}
          {props.conversations.map((c) => (
            <div
              key={c.id}
              className={`group flex items-center gap-1 rounded-lg px-2 py-2 text-sm ${
                c.id === props.activeId ? "bg-surface-muted text-slate-100" : "text-slate-300 hover:bg-white/5"
              }`}
            >
              {editing === c.id ? (
                <input
                  autoFocus
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && commitEdit(c.id)}
                  onBlur={() => commitEdit(c.id)}
                  className="flex-1 rounded bg-black/40 px-1.5 py-0.5 text-sm focus:outline-none"
                />
              ) : (
                <button className="flex flex-1 items-center gap-1.5 truncate text-left" onClick={() => props.onSelect(c.id)}>
                  {c.pinned && <Pin size={12} className="shrink-0 text-nv-green" />}
                  <span className="truncate">{c.title}</span>
                </button>
              )}
              <div className="flex shrink-0 items-center opacity-0 transition group-hover:opacity-100">
                {editing === c.id ? (
                  <button className="rounded p-1 hover:bg-white/10" onClick={() => commitEdit(c.id)}>
                    <Check size={13} />
                  </button>
                ) : (
                  <>
                    <button className="rounded p-1 hover:bg-white/10" title="Pin" onClick={() => props.onTogglePin(c)}>
                      {c.pinned ? <PinOff size={13} /> : <Pin size={13} />}
                    </button>
                    <button className="rounded p-1 hover:bg-white/10" title="Rename" onClick={() => startEdit(c)}>
                      <Pencil size={13} />
                    </button>
                    <button className="rounded p-1 hover:bg-white/10" title="Archive" onClick={() => props.onArchive(c)}>
                      <Archive size={13} />
                    </button>
                    <button className="rounded p-1 text-red-400 hover:bg-white/10" title="Delete" onClick={() => props.onDelete(c.id)}>
                      <Trash2 size={13} />
                    </button>
                  </>
                )}
              </div>
            </div>
          ))}
        </nav>

        <div className="border-t border-white/10 p-2 text-sm">
          <Link to="/settings" className="flex items-center gap-2 rounded-lg px-3 py-2 text-slate-300 hover:bg-white/5">
            <Settings size={16} /> Settings
          </Link>
          <Link to="/usage" className="flex items-center gap-2 rounded-lg px-3 py-2 text-slate-300 hover:bg-white/5">
            <BarChart3 size={16} /> Usage
          </Link>
          {props.isAdmin && (
            <Link to="/admin" className="flex items-center gap-2 rounded-lg px-3 py-2 text-slate-300 hover:bg-white/5">
              <Shield size={16} /> Admin
            </Link>
          )}
          <div className="mt-1 flex items-center justify-between rounded-lg px-3 py-2">
            <span className="truncate text-xs text-slate-400">{props.userEmail}</span>
            <button onClick={props.onLogout} title="Log out" className="rounded p-1 text-slate-400 hover:bg-white/10 hover:text-slate-100">
              <LogOut size={16} />
            </button>
          </div>
        </div>
      </aside>
    </>
  );
}
