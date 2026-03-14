import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { motion, AnimatePresence } from "framer-motion";
import { CheckCircle, XCircle, Info } from "lucide-react";

interface ToastItem {
  id: number;
  type: "success" | "error" | "info";
  message: string;
}

let toastId = 0;
let addToastFn: ((toast: Omit<ToastItem, "id">) => void) | null = null;

export function showToast(type: ToastItem["type"], message: string) {
  addToastFn?.({ type, message });
}

export function ToastContainer() {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  useEffect(() => {
    addToastFn = (toast) => {
      const id = ++toastId;
      setToasts((prev) => [...prev, { ...toast, id }]);
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, 3000);
    };
    return () => {
      addToastFn = null;
    };
  }, []);

  const icons = {
    success: <CheckCircle className="w-5 h-5 text-emerald-400" />,
    error: <XCircle className="w-5 h-5 text-red-400" />,
    info: <Info className="w-5 h-5 text-violet-400" />,
  };

  const borders = {
    success: "border-emerald-500/30",
    error: "border-red-500/30",
    info: "border-violet-500/30",
  };

  return createPortal(
    <div className="fixed top-4 left-1/2 -translate-x-1/2 z-[100] flex flex-col gap-2 pointer-events-none">
      <AnimatePresence>
        {toasts.map((toast) => (
          <motion.div
            key={toast.id}
            initial={{ opacity: 0, y: -20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -20, scale: 0.95 }}
            className={`pointer-events-auto flex items-center gap-3 px-4 py-3 rounded-2xl border ${borders[toast.type]} bg-dark-100/90 backdrop-blur-xl shadow-lg min-w-[280px]`}
          >
            {icons[toast.type]}
            <span className="text-sm text-white/90">{toast.message}</span>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>,
    document.body
  );
}
