'use client';
import { useEffect } from 'react';

interface ToastProps {
  message: string;
  type: 'success' | 'error' | 'info';
  onDismiss: () => void;
}

export function Toast({ message, type, onDismiss }: ToastProps) {
  useEffect(() => {
    const t = setTimeout(onDismiss, 3000);
    return () => clearTimeout(t);
  }, [onDismiss]);

  const bg = type === 'success' ? 'bg-green-700' : type === 'error' ? 'bg-red-700' : 'bg-blue-700';

  return (
    <div className={`fixed bottom-4 right-4 ${bg} text-white px-4 py-3 rounded-lg shadow-lg z-50 flex items-center gap-2 max-w-sm`}>
      <span>{type === 'success' ? '✓' : type === 'error' ? '✗' : 'ℹ'}</span>
      <span className="text-sm">{message}</span>
      <button onClick={onDismiss} className="ml-2 opacity-70 hover:opacity-100" aria-label="Dismiss">×</button>
    </div>
  );
}
