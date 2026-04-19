"use client";

import { useState, useRef, useEffect } from "react";
import { ChevronUp, X, Sparkles } from "lucide-react";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

interface AIAssistantProps {
  onSendMessage?: (message: string) => Promise<string>;
}

const suggestedQuestions = [
  "What should I patch this week?",
  "Show me all critical vulnerabilities",
  "Create a goal for SOC 2 compliance",
  "Which assets are most at risk?",
  "Explain my current risk score",
];

export function AIAssistant({ onSendMessage }: AIAssistantProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content: "Hi! I'm your AI patch assistant. I can help you understand your vulnerabilities, create patching goals, and optimize your schedule. What would you like to know?",
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

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      // Default mock responses if no handler provided
      const response = onSendMessage
        ? await onSendMessage(input)
        : getMockResponse(input);

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: response,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: "I'm having trouble processing that request. Please try again.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

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
        <div className="fixed bottom-6 right-6 w-96 h-[600px] bg-card border border-border rounded-lg shadow-2xl flex flex-col">
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-border">
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-primary" />
              <h3 className="font-semibold">PatchGuide Assistant</h3>
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
                <div
                  className={`max-w-[80%] rounded-lg p-3 ${
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

          {/* Suggestions */}
          {messages.length === 1 && (
            <div className="px-4 pb-2">
              <p className="text-xs text-neutral-400 mb-2">Suggested questions:</p>
              <div className="flex flex-wrap gap-2">
                {suggestedQuestions.map((question, index) => (
                  <button
                    key={index}
                    onClick={() => setInput(question)}
                    className="text-xs bg-neutral-800 hover:bg-neutral-700 px-2 py-1 rounded transition-colors"
                  >
                    {question}
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

// Mock responses for demo
function getMockResponse(input: string): string {
  const lowerInput = input.toLowerCase();

  if (lowerInput.includes("patch") && lowerInput.includes("week")) {
    return `Based on your current risk profile, here are the top priorities for this week:

1. **CVE-2024-1234** (Critical) - Affects 12 internet-facing servers
2. **CVE-2024-5678** (KEV Listed) - Active exploitation detected
3. **CVE-2024-9012** (High) - Database servers at risk

Total risk reduction if patched: 2,340 points (28% improvement)

Would you like me to create a patch bundle for these?`;
  }

  if (lowerInput.includes("critical")) {
    return `You currently have 23 critical vulnerabilities:

• 12 affecting internet-exposed assets
• 8 on internal production servers
• 3 on development systems

The highest risk is CVE-2024-1234 with a CVSS score of 9.8 and active exploitation in the wild.

Would you like to see the full list or create a goal to eliminate these?`;
  }

  if (lowerInput.includes("soc") || lowerInput.includes("compliance")) {
    return `I can help you create a SOC 2 compliance goal. Based on your current vulnerabilities:

• **Timeline needed**: 45-60 days to patch all high/critical
• **Maintenance windows required**: 8-10
• **Risk tolerance**: Conservative recommended

Shall I create a goal targeting July 1st for your SOC 2 audit?`;
  }

  if (lowerInput.includes("risk score")) {
    return `Your current total risk score is **84,720**.

**Breakdown:**
• Critical vulnerabilities: 45,200 (53%)
• High vulnerabilities: 28,100 (33%)
• Medium vulnerabilities: 9,420 (11%)
• Low vulnerabilities: 2,000 (3%)

**Trend**: Down 12.4% over the last 7 days

The score is calculated using 8 factors including CVSS, EPSS, KEV listing, asset criticality, and runtime analysis from Snapper.`;
  }

  return `I understand you're asking about "${input}". I can help you with:

• Analyzing vulnerabilities and risk
• Creating and optimizing patching goals
• Understanding your security posture
• Planning maintenance windows
• Tracking patch success rates

What specific aspect would you like to explore?`;
}