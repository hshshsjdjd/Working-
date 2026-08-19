export interface User {
  id: string;
  email: string;
  role: "user" | "admin";
  is_active: boolean;
  created_at: string;
}

export interface Model {
  id: string;
  display_name: string;
  description: string;
  capabilities: string[];
  context_window: number;
  supports_vision: boolean;
  enabled: boolean;
  sort_order: number;
}

export interface Conversation {
  id: string;
  title: string;
  model_id: string | null;
  system_prompt: string | null;
  pinned: boolean;
  archived: boolean;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  model_id: string | null;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  created_at: string;
}

export interface Settings {
  theme: "dark" | "light" | "system" | "amoled";
  default_model_id: string | null;
  temperature: number;
  top_p: number;
  max_tokens: number;
  system_prompt: string | null;
  streaming: boolean;
  markdown: boolean;
  code_highlight: boolean;
  auto_scroll: boolean;
}

export interface UsageSummary {
  total_requests: number;
  successful_requests: number;
  failed_requests: number;
  total_tokens: number;
  current_model: string | null;
  recent: Array<{
    model_id: string | null;
    endpoint: string;
    success: boolean;
    latency_ms: number | null;
    total_tokens: number | null;
    created_at: string;
  }>;
}

export interface UploadedFile {
  id: string;
  original_name: string;
  mime_type: string;
  size_bytes: number;
  conversation_id: string | null;
  created_at: string;
}
