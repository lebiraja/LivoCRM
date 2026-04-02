import { motion } from "framer-motion";
import { Check, X, AlertCircle } from "lucide-react";
import type { ConfirmationRequest } from "@/types";

interface Props {
  confirmation: ConfirmationRequest;
  onConfirm: (id: string) => void;
  onDismiss: (id: string) => void;
}

export function ConfirmationCard({ confirmation, onConfirm, onDismiss }: Props) {
  const { action } = confirmation;

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: "auto" }}
      exit={{ opacity: 0, height: 0 }}
      className="mt-3 rounded-xl border border-amber-200 bg-amber-50 p-4 shadow-sm"
    >
      {/* Header */}
      <div className="flex items-center gap-2 text-amber-700">
        <AlertCircle size={16} />
        <span className="text-xs font-semibold uppercase tracking-wide">
          Confirm Action
        </span>
      </div>

      {/* Description */}
      <p className="mt-2 text-sm text-amber-900">{action.description}</p>

      {/* Action details */}
      <div className="mt-2 rounded-lg bg-white/60 p-2 text-xs text-amber-800 font-mono">
        <span className="font-semibold">{action.type}</span>{" "}
        <span className="opacity-70">→ {action.entity}</span>
      </div>

      {/* Buttons */}
      <div className="mt-3 flex gap-2">
        <button
          onClick={() => onConfirm(confirmation.id)}
          className="inline-flex items-center gap-1 rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white shadow-sm hover:bg-emerald-700 transition-colors"
        >
          <Check size={14} /> Confirm
        </button>
        <button
          onClick={() => onDismiss(confirmation.id)}
          className="inline-flex items-center gap-1 rounded-lg bg-white px-3 py-1.5 text-xs font-medium text-gray-700 shadow-sm ring-1 ring-gray-200 hover:bg-gray-50 transition-colors"
        >
          <X size={14} /> Dismiss
        </button>
      </div>
    </motion.div>
  );
}
