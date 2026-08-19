import { memo, useState, type ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import { Check, Copy } from "lucide-react";

function extractText(node: ReactNode): string {
  if (typeof node === "string") return node;
  if (Array.isArray(node)) return node.map(extractText).join("");
  if (node && typeof node === "object" && "props" in node) {
    const props = (node as { props?: { children?: ReactNode } }).props;
    return extractText(props?.children);
  }
  return "";
}

function CodeToolbar({ code, language }: { code: string; language: string }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };
  return (
    <div className="flex items-center justify-between rounded-t-lg border-b border-white/10 bg-[#0b0f14] px-3 py-1.5 text-xs text-slate-400">
      <span className="font-mono lowercase">{language || "code"}</span>
      <button
        onClick={copy}
        className="flex items-center gap-1 rounded px-1.5 py-0.5 transition hover:bg-white/10 hover:text-slate-100"
        aria-label="Copy code"
      >
        {copied ? <Check size={13} /> : <Copy size={13} />}
        {copied ? "Copied" : "Copy"}
      </button>
    </div>
  );
}

function PreBlock({ children }: { children?: ReactNode }) {
  const child = Array.isArray(children) ? children[0] : children;
  let language = "";
  const className: string =
    (child as { props?: { className?: string } })?.props?.className || "";
  const match = /language-(\w+)/.exec(className);
  if (match) language = match[1];
  const code = extractText(children).replace(/\n$/, "");
  return (
    <div className="my-3 overflow-hidden rounded-lg">
      <CodeToolbar code={code} language={language} />
      <pre>{children}</pre>
    </div>
  );
}

export const Markdown = memo(function Markdown({ content }: { content: string }) {
  return (
    <div className="prose-chat max-w-none break-words">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[[rehypeHighlight, { detect: true, ignoreMissing: true }]]}
        components={{ pre: PreBlock as never }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
});
