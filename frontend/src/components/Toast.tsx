"use client";

import { useState, useCallback } from "react";

export type ToastType = "success" | "error" | "info";

export interface ToastState {
  message: string;
  type: ToastType;
}

export function useToast() {
  const [toast, setToast] = useState<ToastState | null>(null);

  const showToast = useCallback((message: string, type: ToastType = "success") => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3500);
  }, []);

  const dismissToast = useCallback(() => setToast(null), []);

  return { toast, showToast, dismissToast };
}

export function ToastNotification({ toast, onDismiss }: { toast: ToastState | null; onDismiss?: () => void }) {
  if (!toast) return null;

  const bg =
    toast.type === "success" ? "bg-green-700 border-green-600" :
    toast.type === "error"   ? "bg-red-700 border-red-600" :
                               "bg-blue-700 border-blue-600";

  const icon =
    toast.type === "success" ? "✓" :
    toast.type === "error"   ? "✕" : "ℹ";

  return (
    <div
      className={`fixed bottom-5 right-5 px-5 py-3 rounded-lg text-white z-[9999] shadow-xl flex items-center gap-3 border text-sm font-medium ${bg}`}
      role="status"
      aria-live="polite"
    >
      <span className="text-base leading-none">{icon}</span>
      <span className="flex-1">{toast.message}</span>
      {onDismiss && (
        <button
          onClick={onDismiss}
          className="ml-2 opacity-70 hover:opacity-100 text-lg leading-none"
          aria-label="Dismiss notification"
        >
          ×
        </button>
      )}
    </div>
  );
}
