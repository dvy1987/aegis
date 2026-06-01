import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

type Tone = "sage" | "clay" | "neutral";

const tones: Record<Tone, string> = {
  sage: "border-l-accent-sage bg-accent-sage-tint",
  clay: "border-l-accent-clay bg-accent-clay-tint",
  neutral: "border-l-border-strong bg-surface-tertiary",
};

export function Callout({
  tone = "neutral",
  label,
  children,
  className,
}: {
  tone?: Tone;
  label?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "rounded-md border-l-2 px-4 py-3 font-body text-base text-text-primary",
        tones[tone],
        className,
      )}
    >
      {label && (
        <p className="mb-1 font-body text-sm text-text-secondary">{label}</p>
      )}
      {children}
    </div>
  );
}
