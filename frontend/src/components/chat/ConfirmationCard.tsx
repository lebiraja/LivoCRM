import { motion } from "framer-motion";
import { Check, X, AlertCircle } from "lucide-react";
import type { ConfirmationPayload } from "@/types";

interface Props {
  confirmation: ConfirmationPayload;
  onConfirm: () => void;
  onDismiss: () => void;
}

export function ConfirmationCard({ confirmation, onConfirm, onDismiss }: Props) {
  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: "auto" }}
      exit={{ opacity: 0, height: 0 }}
      className="mt-3 min-w-0 border-l-2 border-warning bg-card p-4"
    >
      {/* Header */}
      <div className="flex items-center gap-2 text-warning">
        <AlertCircle size={16} aria-hidden="true" />
        <span className="text-xs font-semibold tracking-wide uppercase">Confirm Action</span>
      </div>

      {/* Message */}
      <p className="mt-2 text-sm break-words">{confirmation.message}</p>

      {/* Action details */}
      <div className="mt-2 rounded-md bg-muted p-2 font-mono text-xs break-words text-muted-foreground">
        <span className="font-semibold text-foreground">{confirmation.entity_type}</span>{" "}
        <span>→ {confirmation.intent}</span>
      </div>

      {/* Buttons */}
      <div className="mt-3 flex flex-wrap gap-2">
        <button
          onClick={onConfirm}
          className="inline-flex min-h-11 items-center gap-1 rounded-md bg-primary px-3 text-xs font-medium text-primary-foreground transition-colors hover:bg-primary/90 md:min-h-8"
        >
          <Check size={14} aria-hidden="true" /> Confirm
        </button>
        <button
          onClick={onDismiss}
          className="inline-flex min-h-11 items-center gap-1 rounded-md border border-border bg-background px-3 text-xs font-medium text-foreground transition-colors hover:bg-muted md:min-h-8"
        >
          <X size={14} aria-hidden="true" /> Dismiss
        </button>
      </div>
    </motion.div>
  );
}
