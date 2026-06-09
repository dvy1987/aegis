import type { HTMLAttributes } from "react";
import { cn } from "@/lib/cn";

/** Uppercase, letter-spaced JetBrains Mono label — the "instrument" voice. */
export function MonoLabel({ className, children, ...rest }: HTMLAttributes<HTMLSpanElement>) {
  return (
    <span className={cn("sc-label", className)} {...rest}>
      {children}
    </span>
  );
}
