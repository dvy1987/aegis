"use client";

import { useEffect, useRef } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { EASE_OUT_EXPO } from "@/lib/motion";
import { GlassPanel } from "@/components/showcase/primitives/GlassPanel";
import { MonoLabel } from "@/components/showcase/primitives/MonoLabel";

export type CaseDocumentKind = "denial" | "clinical";

export function CaseDocumentModal({
  open,
  title,
  eyebrow,
  body,
  onClose,
}: {
  open: boolean;
  title: string;
  eyebrow: string;
  body: string;
  onClose: () => void;
}) {
  const reduce = useReducedMotion();
  const panelRef = useRef<HTMLDivElement>(null);

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

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-[80] flex items-end justify-center p-4 sm:items-center sm:p-6"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: reduce ? 0 : 0.25 }}
          role="presentation"
        >
          <button
            type="button"
            aria-label="Close"
            className="absolute inset-0 cursor-default"
            style={{ background: "oklch(0% 0 0 / 0.62)" }}
            onClick={onClose}
          />

          <motion.div
            ref={panelRef}
            tabIndex={-1}
            role="dialog"
            aria-modal="true"
            aria-labelledby="case-document-title"
            className="relative z-[81] flex w-full max-w-2xl flex-col outline-none"
            style={{ maxHeight: "min(88dvh, 40rem)" }}
            initial={{ opacity: 0, y: 24, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 16, scale: 0.99 }}
            transition={{ duration: reduce ? 0 : 0.45, ease: EASE_OUT_EXPO }}
          >
            <GlassPanel variant="elevated" className="flex min-h-0 flex-1 flex-col overflow-hidden">
              <header
                className="flex shrink-0 items-start justify-between gap-4 border-b px-6 py-5"
                style={{ borderColor: "var(--sc-hairline)" }}
              >
                <div className="min-w-0">
                  <MonoLabel>{eyebrow}</MonoLabel>
                  <h2 id="case-document-title" className="mt-2 sc-h2" style={{ fontSize: "1.35rem" }}>
                    {title}
                  </h2>
                </div>
                <button
                  type="button"
                  onClick={onClose}
                  aria-label="Close dialog"
                  className="shrink-0 rounded-full px-3 py-1.5 sc-mono transition-colors hover:opacity-80"
                  style={{
                    border: "1px solid var(--sc-hairline-strong)",
                    color: "var(--sc-text-2)",
                  }}
                >
                  Close
                </button>
              </header>

              <div className="min-h-0 flex-1 overflow-y-auto px-6 py-5">
                <p
                  className="sc-body whitespace-pre-wrap"
                  style={{ fontSize: "0.95rem", color: "var(--sc-text-2)", lineHeight: 1.65 }}
                >
                  {body || "No content available for this case."}
                </p>
              </div>
            </GlassPanel>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
