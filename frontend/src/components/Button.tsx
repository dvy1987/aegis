import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

type Variant = "primary" | "secondary" | "ghost";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
}

const base =
  "inline-flex items-center justify-center gap-2.5 rounded-md font-body text-base font-medium leading-none " +
  "px-6 h-12 text-center whitespace-nowrap " +
  "[&_svg]:block [&_svg]:shrink-0 " +
  "active:scale-[0.97] disabled:opacity-50 disabled:pointer-events-none aegis-button";

const variants: Record<Variant, string> = {
  primary:
    "bg-accent-sage text-text-on-accent hover:bg-accent-sage-deep",
  secondary:
    "bg-surface-secondary text-text-primary border border-border-default hover:border-border-strong",
  ghost:
    "bg-transparent text-text-primary hover:bg-surface-tertiary",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  function Button({ variant = "primary", className, ...rest }, ref) {
    return (
      <button
        ref={ref}
        className={cn(base, variants[variant], className)}
        {...rest}
      />
    );
  },
);
