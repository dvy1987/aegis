import { StatusDot } from "@/components/ui/StatusDot";

export function DiffCard({ whatChanged }: { whatChanged: string[] }) {
  if (!whatChanged.length) return null;
  return (
    <section className="flex flex-col gap-4">
      <h2 className="font-display text-display-md font-semibold tracking-tight">
        What changed, and why.
      </h2>
      <ul className="flex flex-col gap-3">
        {whatChanged.map((line, i) => (
          <li key={i} className="flex items-start gap-3 font-body text-base text-text-secondary">
            <StatusDot className="mt-2 shrink-0" />
            {line}
          </li>
        ))}
      </ul>
    </section>
  );
}
