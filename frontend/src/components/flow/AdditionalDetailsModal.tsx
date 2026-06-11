"use client";

import { useEffect, useId, useRef, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Button } from "@/components/Button";
import { TextArea } from "@/components/ui/TextArea";

export function AdditionalDetailsModal({
  open,
  initialValue,
  onClose,
  onSave,
}: {
  open: boolean;
  initialValue: string;
  onClose: () => void;
  onSave: (text: string) => void;
}) {
  const reduced = useReducedMotion();
  const titleId = useId();
  const panelRef = useRef<HTMLDivElement>(null);
  const [text, setText] = useState(initialValue);

  useEffect(() => {
    if (open) setText(initialValue);
  }, [open, initialValue]);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  useEffect(() => {
    if (open) panelRef.current?.focus();
  }, [open]);

  function save() {
    onSave(text.trim());
    onClose();
  }

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-50 flex items-end justify-center p-4 sm:items-center sm:p-6"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: reduced ? 0 : 0.2 }}
          role="presentation"
        >
          <button
            type="button"
            aria-label="Close"
            className="absolute inset-0 bg-black/55"
            onClick={onClose}
          />

          <motion.div
            ref={panelRef}
            tabIndex={-1}
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            className="relative z-10 flex w-full max-w-lg flex-col rounded-md border border-border-default bg-surface-primary p-6 shadow-lg outline-none"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 12 }}
            transition={{ duration: reduced ? 0 : 0.3 }}
          >
            <h2 id={titleId} className="font-display text-display-sm font-semibold tracking-tight">
              Add more details
            </h2>
            <p className="mt-2 font-body text-sm text-text-secondary">
              Anything else you or your doctor want mentioned. You can work it into the draft on the
              next screen.
            </p>

            <div className="mt-6">
              <TextArea
                label="Additional details"
                hint="Optional. Names, dates, test results, or what your doctor told you."
                value={text}
                onChange={(e) => setText(e.target.value)}
                rows={6}
              />
            </div>

            <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:justify-end">
              <Button type="button" variant="ghost" onClick={onClose}>
                Cancel
              </Button>
              <Button type="button" onClick={save}>
                Save details
              </Button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
