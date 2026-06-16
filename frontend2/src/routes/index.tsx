import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { Send, ShieldCheck, Sparkles, Wifi, WifiOff } from "lucide-react";
import {
  checkHealth,
  sendChatMessage,
  type ChatResponse,
} from "@/lib/netsol-api";
import { ChatMessageItem, type UiMessage } from "@/components/ChatMessageItem";
import { BackendSettings } from "@/components/BackendSettings";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { Toaster } from "@/components/ui/sonner";
import heroBg from "@/assets/hero-bg.jpg";
import botLogo from "@/assets/bot-logo.png";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "NetSol AI Assistant — RAG Chatbot" },
      {
        name: "description",
        content:
          "Chat with NetSol's AI assistant. Ask about NFS Ascent, asset finance, leasing solutions and more — powered by a Retrieval-Augmented Generation engine.",
      },
      { property: "og:title", content: "NetSol AI Assistant — RAG Chatbot" },
      {
        property: "og:description",
        content: "Context-aware answers about NetSol products, powered by RAG.",
      },
    ],
  }),
  component: ChatPage,
});

const SUGGESTIONS = [
  "What products does NetSol offer?",
  "Tell me about NFS Ascent.",
  "How does NetSol support asset finance?",
  "What industries does NetSol serve?",
];

function newSessionId() {
  return `session-${Math.random().toString(36).slice(2, 10)}-${Date.now()}`;
}

function ChatPage() {
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [online, setOnline] = useState<boolean | null>(null);
  const [sessionId, setSessionId] = useState("");

  const inputRef = useRef<HTMLTextAreaElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setSessionId(newSessionId());
  }, []);

  const refreshHealth = async () => setOnline(await checkHealth());

  useEffect(() => {
    refreshHealth();
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  useEffect(() => {
    if (!loading) inputRef.current?.focus();
  }, [loading]);

  const send = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || loading) return;

    const userMsg: UiMessage = {
      id: `u-${Date.now()}`,
      role: "user",
      content: trimmed,
    };
    setMessages((m) => [...m, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res: ChatResponse = await sendChatMessage(sessionId, trimmed);
      setMessages((m) => [
        ...m,
        {
          id: `a-${Date.now()}`,
          role: "assistant",
          content: res.answer,
          sources: res.sources,
        },
      ]);
      setOnline(true);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Something went wrong.";
      toast.error("Could not get a response", { description: message });
      setMessages((m) => [
        ...m,
        {
          id: `e-${Date.now()}`,
          role: "assistant",
          content: `⚠️ ${message}\n\nCheck the **Backend** connection in the top-right.`,
        },
      ]);
      refreshHealth();
    } finally {
      setLoading(false);
    }
  };

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    send(input);
  };

  return (
    <div className="relative min-h-screen overflow-hidden">
      <Toaster />
      {/* Background */}
      <img
        src={heroBg}
        alt=""
        aria-hidden
        className="pointer-events-none absolute inset-0 size-full object-cover opacity-40"
      />
      <div
        className="pointer-events-none absolute inset-0"
        style={{ background: "var(--gradient-hero)" }}
      />
      <div className="pointer-events-none absolute inset-0 bg-background/55" />

      <div className="relative z-10 mx-auto flex min-h-screen max-w-3xl flex-col px-4">
        {/* Header */}
        <header className="flex items-center justify-between gap-3 py-5">
          <div className="flex items-center gap-3">
            <img src={botLogo} alt="NetSol AI" className="size-10" width={40} height={40} />
            <div>
              <h1 className="text-lg font-bold leading-tight">
                NetSol <span className="text-gradient">AI Assistant</span>
              </h1>
              <p className="text-xs text-muted-foreground">RAG-powered · Gemini 2.5 Flash</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span
              className={`hidden items-center gap-1.5 rounded-full px-2.5 py-1 text-xs sm:flex glass ${
                online === false ? "text-destructive" : "text-primary"
              }`}
            >
              {online === false ? <WifiOff className="size-3.5" /> : <Wifi className="size-3.5" />}
              {online === null ? "Checking…" : online ? "Online" : "Offline"}
            </span>
            <BackendSettings onSaved={refreshHealth} />
          </div>
        </header>

        {/* Messages */}
        <main className="flex flex-1 flex-col gap-4 overflow-y-auto pb-4">
          {messages.length === 0 ? (
            <div className="flex flex-1 flex-col items-center justify-center text-center">
              <div className="glass mb-5 flex size-16 items-center justify-center rounded-2xl shadow-[var(--shadow-glow)]">
                <Sparkles className="size-7 text-primary" />
              </div>
              <h2 className="mb-2 text-2xl font-bold">How can I help you today?</h2>
              <p className="mb-6 max-w-md text-sm text-muted-foreground">
                Ask anything about NetSol's products, platforms, and asset finance &
                leasing solutions. Answers are grounded in source documents.
              </p>
              <div className="grid w-full max-w-lg gap-2 sm:grid-cols-2">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    onClick={() => send(s)}
                    className="glass rounded-xl px-4 py-3 text-left text-sm transition-colors hover:bg-[var(--glass-border)]"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((m) => <ChatMessageItem key={m.id} msg={m} />)
          )}

          {loading && (
            <div className="flex animate-fade-up items-center gap-3">
              <div className="flex size-9 items-center justify-center rounded-full bg-[image:var(--gradient-brand)] shadow-[var(--shadow-glow)]">
                <Sparkles className="size-4 text-primary-foreground" />
              </div>
              <div className="glass flex items-center gap-1.5 rounded-2xl rounded-tl-sm px-4 py-3">
                <span className="typing-dot" style={{ animationDelay: "0ms" }} />
                <span className="typing-dot" style={{ animationDelay: "150ms" }} />
                <span className="typing-dot" style={{ animationDelay: "300ms" }} />
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </main>

        {/* Composer */}
        <footer className="sticky bottom-0 pb-5 pt-2">
          <form onSubmit={onSubmit} className="glass-strong rounded-2xl p-2 shadow-[var(--shadow-glass)]">
            <div className="flex items-end gap-2">
              <Textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    send(input);
                  }
                }}
                placeholder="Ask about NetSol products…"
                rows={1}
                className="max-h-40 min-h-[44px] resize-none border-0 bg-transparent shadow-none focus-visible:ring-0"
              />
              <Button
                type="submit"
                variant="brand"
                size="icon"
                disabled={loading || !input.trim()}
                aria-label="Send message"
              >
                <Send className="size-4" />
              </Button>
            </div>
          </form>
          <p className="mt-2 flex items-center justify-center gap-1.5 text-center text-[11px] text-muted-foreground">
            <ShieldCheck className="size-3" />
            Responses are generated from NetSol source documents and may be incomplete.
          </p>
        </footer>
      </div>
    </div>
  );
}
