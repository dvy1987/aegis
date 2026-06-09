"use client";

import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

export type PipelineKind = "draft" | "judge" | "memory" | "optimize" | "approve" | "promote";

const paths: Record<PipelineKind, ReactNode> = {
  draft: (
    <>
      <rect x="5" y="3.5" width="12" height="17" rx="1.5" />
      <path d="M8 8h6M8 11.5h6M8 15h4" />
    </>
  ),
  judge: (
    <>
      <path d="M12 4v15" />
      <path d="M5 7h14" />
      <path d="M5 7l-2.5 5h5z" />
      <path d="M19 7l-2.5 5h5z" />
      <path d="M8 20h8" />
    </>
  ),
  memory: (
    <>
      <ellipse cx="12" cy="6" rx="7" ry="2.6" />
      <path d="M5 6v6c0 1.4 3.1 2.6 7 2.6s7-1.2 7-2.6V6" />
      <path d="M5 12v6c0 1.4 3.1 2.6 7 2.6s7-1.2 7-2.6v-6" />
    </>
  ),
  optimize: (
    <>
      <path d="M19 5a8 8 0 1 0 1.5 6" />
      <path d="M20.5 4v4h-4" />
    </>
  ),
  approve: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M8.5 12.2l2.4 2.4 4.6-5" />
    </>
  ),
  promote: (
    <>
      <path d="M12 19V7" />
      <path d="M7 11l5-5 5 5" />
      <path d="M5 21h14" />
    </>
  ),
};

/** Bespoke pipeline node mark — avoids the generic-Lucide tell. */
export function PipelineIcon({
  kind,
  active = false,
  size = 24,
  className,
}: {
  kind: PipelineKind;
  active?: boolean;
  size?: number;
  className?: string;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke={active ? "var(--sc-accent)" : "var(--sc-text-3)"}
      strokeWidth={1.4}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
      className={cn("transition-[stroke,filter] duration-500", className)}
      style={active ? { filter: "drop-shadow(0 0 6px var(--sc-accent-glow))" } : undefined}
    >
      {paths[kind]}
    </svg>
  );
}
