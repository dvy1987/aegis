"use client";

import { AnimatePresence, motion } from "framer-motion";
import type { ShowcaseRunSession } from "@/lib/types";
import { StatusOrb } from "@/components/showcase/fx/StatusOrb";

/**
 * Sticky "now playing" HUD — keeps STATUS · STAGE · N/M legible on camera even
 * when the matrix is scrolled off-screen. Appears once a session exists.
 */
export function StatusHUD({ session }: { session: ShowcaseRunSession | null }) {
  return (
    <AnimatePresence>
      {session && (
        <motion.div
          initial={{ opacity: 0, y: -12 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -12 }}
          transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
          className="sc-glass-panel fixed right-4 top-4 z-[150] flex items-center gap-3 px-4 py-2 md:right-8 md:top-8"
          role="status"
          aria-live="polite"
        >
          <StatusOrb status={session.status} size={10} />
          <span className="sc-mono" style={{ color: "var(--sc-text-2)" }}>
            {session.status.replaceAll("_", " ").toUpperCase()}
          </span>
          <span aria-hidden style={{ color: "var(--sc-text-3)" }}>
            ·
          </span>
          <span className="sc-mono">{session.diagnostics.stage.replaceAll("_", " ").toUpperCase()}</span>
          <span aria-hidden style={{ color: "var(--sc-text-3)" }}>
            ·
          </span>
          <span className="sc-mono">
            {session.diagnostics.completed_cases}/{session.diagnostics.total_cases || "—"}
          </span>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
