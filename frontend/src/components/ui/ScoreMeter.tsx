export function ScoreMeter({
  score,
  threshold,
  label,
}: {
  score: number;
  threshold?: number;
  label?: string;
}) {
  const pct = Math.max(0, Math.min(1, score)) * 100;
  return (
    <div className="flex flex-col gap-1">
      {label && <span className="font-body text-sm text-text-secondary">{label}</span>}
      <div className="relative h-2 w-full rounded-pill bg-surface-tertiary">
        <div className="h-2 rounded-pill bg-accent-sage" style={{ width: `${pct}%` }} />
        {threshold != null && (
          <div
            className="absolute top-[-2px] h-3 w-px bg-border-strong"
            style={{ left: `${Math.max(0, Math.min(1, threshold)) * 100}%` }}
            aria-hidden
          />
        )}
      </div>
      <span className="font-mono text-xs text-text-tertiary">
        {score.toFixed(2)}
        {threshold != null ? ` · threshold ${threshold.toFixed(2)}` : ""}
      </span>
    </div>
  );
}
