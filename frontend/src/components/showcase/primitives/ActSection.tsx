"use client";

import type { ReactNode } from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/cn";
import { sectionEnter } from "@/lib/motion";

/**
 * Shared Act container: centered 1200px column, generous cinematic padding, and
 * the Tier-2 enter (blur-in + rise + stagger) once it scrolls into view.
 */
export function ActSection({
  id,
  children,
  className,
  full = false,
}: {
  id: string;
  children: ReactNode;
  className?: string;
  /** Full-viewport act (hero / close). */
  full?: boolean;
}) {
  return (
    <motion.section
      id={id}
      variants={sectionEnter}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, amount: 0.25 }}
      className={cn(
        "mx-auto w-full px-6 md:px-12",
        full ? "flex min-h-dvh flex-col justify-center py-24" : "py-24 md:py-32",
        className,
      )}
      style={{ maxWidth: "var(--sc-container-max)" }}
    >
      {children}
    </motion.section>
  );
}
