import { cn } from "@/lib/cn";

export function Disclaimer({ className }: { className?: string }) {
  return (
    <p className={cn("font-body text-sm text-text-tertiary", className)}>
      This is a draft for your review. It is not legal or medical advice. A person should read it
      before you file.
    </p>
  );
}
