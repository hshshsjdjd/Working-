import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Menu, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { Sidebar } from "../components/Sidebar";
import { ModelSelector } from "../components/ModelSelector";
import { MessageItem } from "../components/MessageItem";
import { Composer } from "../components/Composer";
import { api, ApiError } from "../lib/api";
import { streamChat } from "../lib/streaming";
import { useAuth } from "../context/AuthContext";
import type { Conversation, Message, Model, Settings } from "../lib/types";

let tempId = 0;
const nextTempId = () => `temp-${++tempId}`;

export function ChatPage() {
  const { user, logout } = useAuth();
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [selectedModel, setSelectedModel] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [prefill, setPrefill] = useState<string | undefined>(undefined);
  const abortRef = useRef<AbortController | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const { data: models = [] } = useQuery({
    queryKey: ["models"],
    queryFn: () => api<Model[]>("/api/models"),
  });
  const { data: settings } = useQuery({
    queryKey: ["settings"],
    queryFn: () => api<Settings>("/api/settings"),
  });
  const { data: conversations = [] } = useQuery({
    queryKey: ["conversations", search],
    queryFn: () =>
      api<Conversation[]>(`/api/conversations${search ? `?search=${encodeURIComponent(search)}` : ""}`),
  });

  useEffect(() => {
    if (!selectedModel) {
      setSelectedModel(settings?.default_model_id || models[0]?.id || null);
    }
  }, [settings, models, selectedModel]);

  const loadConversation = useCallback(async (id: string) => {
    setActiveId(id);
    setSidebarOpen(false);
    const msgs = await api<Message[]>(`/api/conversations/${id}/messages`);
    setMessages(msgs);
    const conv = conversations.find((c) => c.id === id);
    if (conv?.model_id) setSelectedModel(conv.model_id);
  }, [conversations]);

  const startNewChat = () => {
    setActiveId(null);
    setMessages([]);
    setSidebarOpen(false);
    setSelectedModel(settings?.default_model_id || models[0]?.id || null);
  };

  useEffect(() => {
    if (settings?.auto_scroll !== false) {
      scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
    }
  }, [messages, settings?.auto_scroll]);

  const runStream = useCallback(
    async (conversationId: string, content: string, fileIds: string[], regenerate: boolean) => {
      const controller = new AbortController();
      abortRef.current = controller;
      setStreaming(true);

      const assistantTempId = nextTempId();
      setMessages((prev) => [
        ...prev,
        {
          id: assistantTempId,
          conversation_id: conversationId,
          role: "assistant",
          content: "",
          model_id: selectedModel,
          prompt_tokens: null,
          completion_tokens: null,
          created_at: new Date().toISOString(),
        },
      ]);

      let aborted = false;
      await streamChat(
        {
          conversation_id: conversationId,
          content,
          model_id: selectedModel,
          regenerate,
          file_ids: fileIds,
        },
        {
          onDelta: (text) =>
            setMessages((prev) =>
              prev.map((m) => (m.id === assistantTempId ? { ...m, content: m.content + text } : m)),
            ),
          onError: (data) => {
            toast.error(data.message || "The AI request failed");
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantTempId && !m.content
                  ? { ...m, content: `⚠️ ${data.message}` }
                  : m,
              ),
            );
          },
        },
        controller.signal,
      ).catch((err) => {
        if (err?.name === "AbortError") aborted = true;
        else toast.error("Connection interrupted");
      });

      setStreaming(false);
      abortRef.current = null;
      qc.invalidateQueries({ queryKey: ["conversations"] });

      // On Stop, keep the partial text already shown — the backend persists the
      // same partial, so we avoid racing its save (which would briefly blank the
      // message). Reconcile in the background after it has committed.
      if (aborted) {
        setTimeout(() => {
          api<Message[]>(`/api/conversations/${conversationId}/messages`)
            .then((fresh) => {
              // Only reconcile once the server has the persisted partial, so the
              // visible text is never briefly cleared.
              if (fresh.some((m) => m.role === "assistant" && m.content)) {
                setMessages(fresh);
              }
            })
            .catch(() => {});
        }, 600);
        return;
      }
      // Reconcile with server truth (real ids, tokens, persisted partials).
      const fresh = await api<Message[]>(`/api/conversations/${conversationId}/messages`);
      setMessages(fresh);
    },
    [selectedModel, qc],
  );

  const handleSend = async (content: string, fileIds: string[]) => {
    let convId = activeId;
    try {
      if (!convId) {
        const conv = await api<Conversation>("/api/conversations", {
          method: "POST",
          body: { title: "New chat", model_id: selectedModel },
        });
        convId = conv.id;
        setActiveId(conv.id);
        qc.invalidateQueries({ queryKey: ["conversations"] });
      }
    } catch (err) {
      toast.error(err instanceof ApiError ? err.detail : "Could not start conversation");
      return;
    }

    setMessages((prev) => [
      ...prev,
      {
        id: nextTempId(),
        conversation_id: convId!,
        role: "user",
        content,
        model_id: selectedModel,
        prompt_tokens: null,
        completion_tokens: null,
        created_at: new Date().toISOString(),
      },
    ]);
    await runStream(convId!, content, fileIds, false);
  };

  const handleRegenerate = async () => {
    if (!activeId) return;
    setMessages((prev) => {
      const copy = [...prev];
      if (copy.length && copy[copy.length - 1].role === "assistant") copy.pop();
      return copy;
    });
    await runStream(activeId, "", [], true);
  };

  const stop = () => abortRef.current?.abort();

  const renameConversation = async (id: string, title: string) => {
    await api(`/api/conversations/${id}`, { method: "PATCH", body: { title } });
    qc.invalidateQueries({ queryKey: ["conversations"] });
  };
  const deleteConversation = async (id: string) => {
    await api(`/api/conversations/${id}`, { method: "DELETE" });
    if (activeId === id) startNewChat();
    qc.invalidateQueries({ queryKey: ["conversations"] });
  };
  const togglePin = async (c: Conversation) => {
    await api(`/api/conversations/${c.id}`, { method: "PATCH", body: { pinned: !c.pinned } });
    qc.invalidateQueries({ queryKey: ["conversations"] });
  };
  const archive = async (c: Conversation) => {
    await api(`/api/conversations/${c.id}`, { method: "PATCH", body: { archived: true } });
    if (activeId === c.id) startNewChat();
    qc.invalidateQueries({ queryKey: ["conversations"] });
  };

  const changeModel = async (id: string) => {
    setSelectedModel(id);
    if (activeId) {
      await api(`/api/conversations/${activeId}`, { method: "PATCH", body: { model_id: id } });
      qc.invalidateQueries({ queryKey: ["conversations"] });
    }
  };

  const lastAssistantId = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === "assistant") return messages[i].id;
    }
    return null;
  }, [messages]);

  return (
    <div className="flex h-screen overflow-hidden bg-black">
      <Sidebar
        conversations={conversations}
        activeId={activeId}
        userEmail={user?.email || ""}
        isAdmin={user?.role === "admin"}
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        onNew={startNewChat}
        onSelect={loadConversation}
        onSearch={setSearch}
        onRename={renameConversation}
        onDelete={deleteConversation}
        onTogglePin={togglePin}
        onArchive={archive}
        onLogout={logout}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center gap-2 border-b border-white/10 px-3 py-2.5 sm:px-4">
          <button className="rounded p-2 text-slate-300 hover:bg-white/10 md:hidden" onClick={() => setSidebarOpen(true)}>
            <Menu size={20} />
          </button>
          <ModelSelector models={models} value={selectedModel} onChange={changeModel} />
        </header>

        <div ref={scrollRef} className="flex-1 overflow-y-auto">
          {messages.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center px-6 text-center">
              <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-nv-green/10">
                <Sparkles size={30} className="text-nv-green" />
              </div>
              <h2 className="text-xl font-semibold text-slate-100">How can I help you today?</h2>
              <p className="mt-2 max-w-md text-sm text-slate-500">
                Ask a question, generate code, or paste text to analyze. Responses stream in real time
                from NVIDIA AI models.
              </p>
            </div>
          ) : (
            <div className="pb-4">
              {messages.map((m) => (
                <MessageItem
                  key={m.id}
                  message={m}
                  useMarkdown={settings?.markdown !== false}
                  streaming={streaming && m.id === lastAssistantId}
                  isLastAssistant={m.id === lastAssistantId}
                  onRegenerate={handleRegenerate}
                  onEdit={(content) => setPrefill(content + " ")}
                />
              ))}
            </div>
          )}
        </div>

        <Composer
          conversationId={activeId}
          streaming={streaming}
          prefill={prefill}
          onSend={handleSend}
          onStop={stop}
        />
      </div>
    </div>
  );
}
