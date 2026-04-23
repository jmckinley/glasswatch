"use client";

import { useState, useRef, useEffect } from "react";
import { ChevronUp, X, Sparkles, CheckCircle } from "lucide-react";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  actions_taken?: string[];
  suggested_actions?: string[];
}

interface AIAssistantProps {
  onSendMessage?: (message: string) => Promise<string>;
  apiEndpoint?: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const REAL_API_ENDPOINT = `${API_BASE_URL}/api/v1/agent/chat`;

const starterPrompts = [
  "What needs my attention right now?",
  "Show me critical KEV vulnerabilities",
  "Create a rule blocking Friday deployments",
  "What maintenance windows do we have?",
  "How are we doing on our goals?",
];

export function AIAssistant({ onSendMessage, apiEndpoint }: AIAssistantProps) {
  // Always use real endpoint by default; fall back only if neither is provided
  const effectiveEndpoint = apiEndpoint || REAL_API_ENDPOINT;
  const isDemoMode = !effectiveEndpoint && !onSendMessage;

  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content: isDemoMode
        ? "Hi! I'm your AI patch assistant (Demo Mode). I can help you understand your vulnerabilities, create patching goals, and optimize your schedule.\n\nNote: This is demo mode with mock responses. Configure ANTHROPIC_API_KEY to enable full AI capabilities."
        : "Hi! I'm your Glasswatch AI assistant. Ask me anything — I work with your live data.\n\nTry one of the prompts below, or ask me something.",
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = async (text: string) => {
    if (!text.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: text,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      let response: string;
      let actions_taken: string[] = [];
      let suggested_actions: string[] = [];

      if (effectiveEndpoint) {
        const token =
          typeof window !== "undefined"
            ? localStorage.getItem("glasswatch_token") ||
              localStorage.getItem("glasswatch-token")
            : null;

        const headers: Record<string, string> = {
          "Content-Type": "application/json",
        };
        if (token) {
          headers["Authorization"] = `Bearer ${token}`;
        }
        // Include demo tenant header so requests work without login
        headers["X-Tenant-ID"] = "550e8400-e29b-41d4-a716-446655440000";

        const apiResponse = await fetch(effectiveEndpoint, {
          method: "POST",
          headers,
          body: JSON.stringify({ message: text }),
        });

        if (!apiResponse.ok) {
          throw new Error(`API error: ${apiResponse.status} ${apiResponse.statusText}`);
        }

        const data = await apiResponse.json();
        response = data.response || data.message || "No response from agent";
        actions_taken = data.actions_taken || [];
        suggested_actions = data.suggested_actions || [];
      } else if (onSendMessage) {
        response = await onSendMessage(text);
      } else {
        response = getMockResponse(text);
      }

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: response,
        timestamp: new Date(),
        actions_taken,
        suggested_actions,
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content:
          "I'm having trouble processing that request. Please check your connection and try again.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSend = () => sendMessage(input);

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const isFirstMessage = messages.length === 1;

  return (
    <>
      {/* Floating Button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="fixed bottom-6 right-6 w-14 h-14 bg-primary rounded-full shadow-lg hover:bg-primary/90 transition-all flex items-center justify-center group"
          aria-label="Open AI Assistant"
        >
          <Sparkles className="w-6 h-6 text-background" />
          <span className="absolute -top-8 right-0 bg-neutral-800 text-white text-sm px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
            AI Assistant
          </span>
        </button>
      )}

      {/* Chat Panel */}
      {isOpen && (
        <div className="fixed bottom-6 right-6 w-96 h-[620px] bg-card border border-border rounded-lg shadow-2xl flex flex-col">
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-border">
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-primary" />
              <div>
                <h3 className="font-semibold">Glasswatch Assistant</h3>
                {isDemoMode && (
                  <span className="text-xs text-neutral-400 bg-neutral-800 px-2 py-0.5 rounded mt-1 inline-block">
                    Demo Mode
                  </span>
                )}
              </div>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="text-neutral-400 hover:text-foreground transition-colors"
              aria-label="Close"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${
                  message.role === "user" ? "justify-end" : "justify-start"
                }`}
              >
                <div className="max-w-[85%]">
                  <div
                    className={`rounded-lg p-3 ${
                      message.role === "user"
                        ? "bg-primary text-background"
                        : "bg-neutral-800 text-foreground"
                    }`}
                  >
                    <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                    <p className="text-xs mt-1 opacity-60">
                      {message.timestamp.toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </p>
                  </div>

                  {/* Actions taken chips */}
                  {message.actions_taken && message.actions_taken.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-1.5">
                      {message.actions_taken.map((action, i) => (
                        <span
                          key={i}
                          className="inline-flex items-center gap-1 text-xs bg-green-900/50 text-green-400 border border-green-800 px-2 py-0.5 rounded-full"
                        >
                          <CheckCircle className="w-3 h-3" />
                          {action}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Suggested actions */}
                  {message.suggested_actions && message.suggested_actions.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-1.5">
                      {message.suggested_actions.map((action, i) => (
                        <button
                          key={i}
                          onClick={() => sendMessage(action)}
                          className="text-xs bg-neutral-700 hover:bg-neutral-600 text-neutral-200 px-2 py-1 rounded-full transition-colors"
                        >
                          {action} →
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-neutral-800 rounded-lg p-3 max-w-[80%]">
                  <div className="flex gap-1">
                    <span className="w-2 h-2 bg-neutral-400 rounded-full animate-bounce" />
                    <span className="w-2 h-2 bg-neutral-400 rounded-full animate-bounce delay-100" />
                    <span className="w-2 h-2 bg-neutral-400 rounded-full animate-bounce delay-200" />
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Starter prompts (shown until first user message) */}
          {isFirstMessage && (
            <div className="px-4 pb-2">
              <p className="text-xs text-neutral-400 mb-2">Try asking:</p>
              <div className="flex flex-wrap gap-1.5">
                {starterPrompts.map((prompt, index) => (
                  <button
                    key={index}
                    onClick={() => sendMessage(prompt)}
                    className="text-xs bg-neutral-800 hover:bg-neutral-700 text-neutral-200 px-2 py-1.5 rounded-lg transition-colors text-left"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Input */}
          <div className="p-4 border-t border-border">
            <div className="flex gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask me anything..."
                className="flex-1 bg-neutral-800 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                disabled={isLoading}
              />
              <button
                onClick={handleSend}
                disabled={!input.trim() || isLoading}
                className="p-2 bg-primary text-background rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                aria-label="Send"
              >
                <ChevronUp className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

// Kept for demo fallback
function getMockResponse(input: string): string {
  const lowerInput = input.toLowerCase();

  if (lowerInput.includes("patch") && lowerInput.includes("week")) {
    return `Based on your current risk profile, here are the top priorities for this week:

1. **CVE-2024-1234** (Critical) - Affects 12 internet-facing servers
2. **CVE-2024-5678** (KEV Listed) - Active exploitation detected
3. **CVE-2024-9012** (High) - Database servers at risk

Total risk reduction if patched: 2,340 points (28% improvement).`;
  }

  if (lowerInput.includes("critical")) {
    return `You currently have 23 critical vulnerabilities:

• 12 affecting internet-exposed assets
• 8 on internal production servers
• 3 on development systems

The highest risk is CVE-2024-1234 with a CVSS score of 9.8 and active exploitation in the wild.`;
  }

  return `I understand you're asking about "${input}". I can help you with:

• Analyzing vulnerabilities and risk
• Creating and optimizing patching goals
• Understanding your security posture
• Planning maintenance windows
• Tracking patch success rates

What specific aspect would you like to explore?`;
}
