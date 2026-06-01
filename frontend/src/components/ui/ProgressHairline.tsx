export function ProgressHairline({ ratio }: { ratio: number }) {
  const pct = Math.max(0, Math.min(1, ratio)) * 100;
  return (
    <div
      className="h-px w-full bg-border-subtle"
      role="progressbar"
      aria-valuenow={Math.round(pct)}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div
        className="h-px bg-accent-sage transition-[width] duration-[400ms] ease-[cubic-bezier(0.2,0.8,0.2,1)]"
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}
