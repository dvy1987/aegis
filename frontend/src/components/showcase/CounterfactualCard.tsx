import { ScoreMeter } from "@/components/ui/ScoreMeter";

export function CounterfactualCard({ on, off }: { on: number; off: number }) {
  return (
    <section className="flex flex-col gap-4 rounded-lg border border-border-subtle bg-surface-secondary p-6">
      <h2 className="font-display text-display-md font-semibold tracking-tight">
        Switch off its memory, and quality drops.
      </h2>
      <p className="max-w-prose font-body text-base text-text-secondary">
        The agent reads its own past evaluations before it drafts. Take that memory away and the
        same case scores lower — the memory is doing real work, not decorating the system.
      </p>
      <div className="grid grid-cols-12 gap-8">
        <div className="col-span-12 md:col-span-6">
          <ScoreMeter score={on} label="Memory on" />
        </div>
        <div className="col-span-12 md:col-span-6">
          <ScoreMeter score={off} label="Memory off" />
        </div>
      </div>
      <p className="font-body text-sm text-text-tertiary">
        The memory-off figure is a design target where a measured run is not yet recorded.
      </p>
    </section>
  );
}
