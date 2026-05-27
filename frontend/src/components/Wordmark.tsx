import { cn } from "@/lib/cn";

export function Wordmark({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-2 font-display text-display-sm font-semibold tracking-tight text-text-primary",
        className,
      )}
    >
      <span aria-hidden="true" className="signature-dot" />
      Aegis
    </span>
  );
}
