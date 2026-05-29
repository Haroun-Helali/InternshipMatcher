'use client';

import React, { createContext, useCallback, useContext, useState } from 'react';
import { CheckCircle2, AlertCircle, Info, X } from 'lucide-react';

type ToastKind = 'success' | 'error' | 'info';

interface Toast {
  id: string;
  kind: ToastKind;
  message: string;
}

interface ToastContextValue {
  toast: (kind: ToastKind, message: string) => void;
}

const ToastContext = createContext<ToastContextValue | undefined>(undefined);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const remove = useCallback((id: string) => {
    setToasts((cur) => cur.filter((t) => t.id !== id));
  }, []);

  const toast = useCallback(
    (kind: ToastKind, message: string) => {
      const id = Math.random().toString(36).slice(2, 11);
      setToasts((cur) => [...cur, { id, kind, message }]);
      // Errors stick a bit longer so users can read them.
      const ttl = kind === 'error' ? 6000 : 3500;
      window.setTimeout(() => remove(id), ttl);
    },
    [remove],
  );

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm">
        {toasts.map((t) => (
          <div
            key={t.id}
            role="status"
            className={`flex items-start gap-2 rounded-lg shadow-lg border px-4 py-3 text-sm bg-white dark:bg-gray-800
              ${t.kind === 'success' ? 'border-green-200 dark:border-green-800' : ''}
              ${t.kind === 'error' ? 'border-red-200 dark:border-red-800' : ''}
              ${t.kind === 'info' ? 'border-blue-200 dark:border-blue-800' : ''}`}
          >
            {t.kind === 'success' && <CheckCircle2 className="w-5 h-5 text-green-500 flex-shrink-0" />}
            {t.kind === 'error' && <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />}
            {t.kind === 'info' && <Info className="w-5 h-5 text-blue-500 flex-shrink-0" />}
            <span className="flex-1 text-gray-900 dark:text-gray-100">{t.message}</span>
            <button
              onClick={() => remove(t.id)}
              aria-label="Dismiss"
              className="text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used inside ToastProvider');
  return ctx;
}
