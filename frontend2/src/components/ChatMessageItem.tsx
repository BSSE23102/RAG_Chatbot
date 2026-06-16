import { memo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Bot, ChevronDown, FileText, User } from "lucide-react";
import type { ChatRole, SourceChunk } from "@/lib/netsol-api";
import { cn } from "@/lib/utils";

export interface UiMessage {
  id: string;
  role: ChatRole;
  content: string;
  sources?: SourceChunk[];
}

function fileName(source: string | null) {
  if (!source) return "Unknown source";
  const parts = source.split(/[\\/]/);
  return parts[parts.length - 1] || source;
}

function Sources({ sources }: { sources: SourceChunk[] }) {
  const [open, setOpen] = useState(false);
  if (!sources.length) return null;
  return (
    <div className="mt-3 rounded-xl glass overflow-hidden">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between px-3 py-2 text-xs font-medium text-muted-foreground hover:text-foreground"
      >
        <span className="flex items-center gap-1.5">
          <FileText className="size-3.5" />
          {sources.length} source{sources.length > 1 ? "s" : ""}
        </span>
        <ChevronDown className={cn("size-4 transition-transform", open && "rotate-180")} />
      </button>
      {open && (
        <div className="space-y-2 px-3 pb-3">
          {sources.map((s, i) => (
            <div key={i} className="rounded-lg bg-secondary/50 p-2.5">
              <div className="mb-1 flex items-center justify-between gap-2">
                <span className="truncate text-xs font-semibold text-primary">
                  {fileName(s.source)}
                </span>
                {s.score != null && (
                  <span className="shrink-0 text-[10px] text-muted-foreground">
                    score {s.score.toFixed(3)}
                  </span>
                )}
              </div>
              <p className="line-clamp-4 text-xs text-muted-foreground">{s.content}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export const ChatMessageItem = memo(function ChatMessageItem({ msg }: { msg: UiMessage }) {
  const isUser = msg.role === "user";
  return (
    <div className={cn("flex animate-fade-up gap-3", isUser && "flex-row-reverse")}>
      <div
        className={cn(
          "flex size-9 shrink-0 items-center justify-center rounded-full",
          isUser
            ? "bg-secondary text-secondary-foreground"
            : "bg-[image:var(--gradient-brand)] text-primary-foreground shadow-[var(--shadow-glow)]",
        )}
      >
        {isUser ? <User className="size-4" /> : <Bot className="size-4" />}
      </div>
      <div className={cn("max-w-[78%]", isUser && "flex flex-col items-end")}>
        <div
          className={cn(
            "rounded-2xl px-4 py-2.5 text-sm leading-relaxed",
            isUser
              ? "rounded-tr-sm bg-primary text-primary-foreground"
              : "rounded-tl-sm glass text-foreground",
          )}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap">{msg.content}</p>
          ) : (
            <div className="markdown-body">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
            </div>
          )}
        </div>
        {!isUser && msg.sources && <Sources sources={msg.sources} />}
      </div>
    </div>
  );
});
