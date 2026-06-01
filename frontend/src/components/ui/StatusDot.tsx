import { cn } from "@/lib/cn";

export function StatusDot({
  tone = "sage",
  className,
}: {
  tone?: "sage" | "clay";
  className?: string;
}) {
  return (
    <span
      aria-hidden
      className={cn(
        "inline-block h-1.5 w-1.5 rounded-full",
        tone === "sage" ? "bg-accent-sage" : "bg-accent-clay",
        className,
      )}
    />
  );
}
