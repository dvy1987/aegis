"use client";

import type { ButtonHTMLAttributes, CSSProperties, ReactNode } from "react";
import { cn } from "@/lib/cn";

type IgniteVariant = "primary" | "secondary" | "ghost";

interface IgniteButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: IgniteVariant;
  children: ReactNode;
}

/**
 * Fallback ignite button — matte rest state, accent sweep on hover, bloom on
 * press. Pure CSS sweep so it stays GPU-light. Wraps children + onClick.
 */
export function IgniteButton({
  variant = "primary",
  className,
  children,
  ...rest
}: IgniteButtonProps) {
  const styles: Record<IgniteVariant, CSSProperties> = {
    primary: {
      background: "var(--sc-accent)",
      color: "var(--sc-text-on-accent)",
      borderColor: "var(--sc-accent)",
    },
    secondary: {
      background: "var(--sc-bg-raised)",
      color: "var(--sc-text)",
      borderColor: "var(--sc-hairline-strong)",
    },
    ghost: {
      background: "transparent",
      color: "var(--sc-text-2)",
      borderColor: "var(--sc-hairline)",
    },
  };

  return (
    <button
      className={cn("sc-ignite-btn", `sc-ignite-btn--${variant}`, className)}
      style={styles[variant]}
      {...rest}
    >
      <span className="sc-ignite-btn__sweep" aria-hidden />
      <span className="relative z-[1] inline-flex items-center gap-2">{children}</span>
    </button>
  );
}
