import { forwardRef, type HTMLAttributes } from "react";
import { cn } from "@/lib/cn";

type GlassVariant = "default" | "glass" | "elevated" | "active" | "sunken";

interface GlassPanelProps extends HTMLAttributes<HTMLDivElement> {
  variant?: GlassVariant;
}

const variantClass: Record<GlassVariant, string> = {
  default: "sc-panel",
  glass: "sc-glass-panel",
  elevated: "sc-panel sc-panel--elevated",
  active: "sc-panel sc-panel--active",
  sunken: "sc-panel-sunken",
};

/** Matte graphite glass surface. `active` adds the accent ring + glow. */
export const GlassPanel = forwardRef<HTMLDivElement, GlassPanelProps>(
  function GlassPanel({ variant = "default", className, ...rest }, ref) {
    return <div ref={ref} className={cn(variantClass[variant], className)} {...rest} />;
  },
);
