"use client";

import { useState, useRef, useEffect } from "react";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  actions_taken?: string[];
  suggested_actions?: string[];
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const REAL_API_ENDPOINT = `${API_BASE_URL}/api/v1/agent/chat`;

const SUGGESTED_PROMPTS = [
  ["What needs my attention today?", "Show all KEV vulnerabilities"],
  ["How is our SOC 2 compliance trending?", "Which bundles need approval?"],
  ["What's our mean time to patch?", "List overdue SLA vulnerabilities"],
];

function TypingIndicator() {
  return (
    <div className="flex justify-start">
      <div className="flex items-start gap-3 max-w-[80%]">
        <div className="w-7 h-7 rounded-full bg-indigo-600 flex items-center justify-center text-xs font-bold text-white flex-shrink-0 mt-1">
          AI
        </div>
        <div className="bg-gray-800 rounded-2xl rounded-tl-sm px-4 py-3">
          <div className="flex gap-1 items-center h-4">
            <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
            <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
            <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
          </div>
        </div>
      </div>
    </div>
  );
}

export default function AgentPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    document.title = "AI Security Analyst | Glasswatch";
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const sendMessage = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || isLoading) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: trimmed,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsLoading(true);

    try {
      const token =
        typeof window !== "undefined"
          ? localStorage.getItem("glasswatch_token") ||
            localStorage.getItem("glasswatch-token")
          : null;

      const headers: Record<string, string> = {
        "Content-Type": "application/json",
        "X-Tenant-ID": "550e8400-e29b-41d4-a716-446655440000",
      };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await fetch(REAL_API_ENDPOINT, {
        method: "POST",
        headers,
        body: JSON.stringify({ message: trimmed }),
      });

      let responseText: string;
      let actions_taken: string[] = [];
      let suggested_actions: string[] = [];

      if (res.ok) {
        const data = await res.json();
        responseText = data.response || data.message || "No response from agent.";
        actions_taken = data.actions_taken || [];
        suggested_actions = data.suggested_actions || [];
      } else {
        responseText = `I'm having trouble reaching the backend (${res.status}). Please check your connection and try again.`;
      }

      const aiMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: responseText,
        timestamp: new Date(),
        actions_taken,
        suggested_actions,
      };
      setMessages((prev) => [...prev, aiMsg]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          content: "I'm having trouble processing that request. Please check your connection and try again.",
          timestamp: new Date(),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  const isEmpty = messages.length === 0;

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] max-w-4xl mx-auto">
      {/* Page header */}
      <div className="mb-4 flex-shrink-0">
        <h1 className="text-3xl font-bold text-white">AI Security Analyst</h1>
        <p className="text-gray-400 text-sm mt-1">Ask anything about your vulnerability posture, compliance status, or patch schedule.</p>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto rounded-xl bg-gray-900 border border-gray-700 p-6 space-y-6 min-h-0">
        {isEmpty ? (
          /* Empty state */
          <div className="flex flex-col items-center justify-center h-full text-center gap-6">
            <div>
              <div className="text-5xl mb-3">⚡</div>
              <h2 className="text-2xl font-bold text-white mb-2">Your AI Security Analyst</h2>
              <p className="text-gray-400 max-w-md">
                Ask anything about your vulnerability posture, compliance status, or patch schedule.
              </p>
            </div>

            {/* Prompt chips */}
            <div className="w-full max-w-2xl space-y-3">
              {SUGGESTED_PROMPTS.map((row, rowIdx) => (
                <div key={rowIdx} className="flex gap-3 justify-center flex-wrap">
                  {row.map((prompt) => (
                    <button
                      key={prompt}
                      onClick={() => sendMessage(prompt)}
                      className="border border-gray-700 rounded-lg px-4 py-2 text-sm text-gray-300 hover:border-indigo-500 hover:text-white hover:bg-indigo-950/30 cursor-pointer transition-all"
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              ))}
            </div>
          </div>
        ) : (
          /* Message thread */
          <>
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div className={`flex items-start gap-3 max-w-[80%] ${msg.role === "user" ? "flex-row-reverse" : ""}`}>
                  {msg.role === "assistant" && (
                    <div className="w-7 h-7 rounded-full bg-indigo-600 flex items-center justify-center text-xs font-bold text-white flex-shrink-0 mt-1">
                      AI
                    </div>
                  )}
                  <div className="space-y-2">
                    <div
                      className={`rounded-2xl px-4 py-3 ${
                        msg.role === "user"
                          ? "bg-indigo-600 text-white rounded-tr-sm"
                          : "bg-gray-800 text-gray-100 rounded-tl-sm"
                      }`}
                    >
                      <p className="text-sm whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                      <p className="text-xs mt-1.5 opacity-50">
                        {msg.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </p>
                    </div>

                    {/* Actions taken */}
                    {msg.actions_taken && msg.actions_taken.length > 0 && (
                      <div className="flex flex-wrap gap-1.5">
                        {msg.actions_taken.map((action, i) => (
                          <span
                            key={i}
                            className="inline-flex items-center gap-1 text-xs bg-emerald-900/40 text-emerald-400 border border-emerald-800 px-2 py-0.5 rounded-full"
                          >
                            ✓ {action}
                          </span>
                        ))}
                      </div>
                    )}

                    {/* Suggested follow-up actions */}
                    {msg.suggested_actions && msg.suggested_actions.length > 0 && (
                      <div className="flex flex-wrap gap-1.5">
                        {msg.suggested_actions.map((action, i) => (
                          <button
                            key={i}
                            onClick={() => sendMessage(action)}
                            className="text-xs border border-gray-600 hover:border-indigo-500 text-gray-300 hover:text-white px-2.5 py-1 rounded-full transition-all"
                          >
                            {action} →
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}

            {isLoading && <TypingIndicator />}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input area */}
      <div className="flex-shrink-0 mt-4">
        {/* Prompt chips (when chat has started) */}
        {!isEmpty && (
          <div className="flex flex-wrap gap-2 mb-3">
            {SUGGESTED_PROMPTS.flat().slice(0, 3).map((prompt) => (
              <button
                key={prompt}
                onClick={() => sendMessage(prompt)}
                className="border border-gray-700 rounded-lg px-3 py-1.5 text-xs text-gray-400 hover:border-indigo-500 hover:text-white transition-all"
              >
                {prompt}
              </button>
            ))}
          </div>
        )}

        <div className="bg-gray-800 border border-gray-700 rounded-xl p-4 focus-within:border-indigo-500 transition-colors">
          <label className="block text-xs text-gray-400 mb-2 font-medium">
            Ask your AI security analyst
          </label>
          <div className="flex gap-3 items-end">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="e.g. What critical vulnerabilities need patching this week?"
              rows={2}
              disabled={isLoading}
              className="flex-1 bg-transparent text-white text-sm resize-none focus:outline-none placeholder-gray-500 disabled:opacity-50"
            />
            <button
              onClick={() => sendMessage(input)}
              disabled={!input.trim() || isLoading}
              className="flex-shrink-0 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-700 disabled:text-gray-500 text-white text-sm font-medium rounded-lg transition-colors"
            >
              {isLoading ? "…" : "Send"}
            </button>
          </div>
          <p className="text-xs text-gray-600 mt-2">Press Enter to send · Shift+Enter for new line</p>
        </div>
      </div>
    </div>
  );
}
