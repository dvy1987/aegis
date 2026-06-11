"use client";

import { CounterfactualCard } from "@/components/showcase/versus/CounterfactualCard";

export function ActIntelligence({ on, off }: { on: number; off: number }) {
  return (
    <section
      id="intelligence"
      className="mx-auto flex w-full flex-col gap-14 px-6 py-24 md:px-12 md:py-32"
      style={{ maxWidth: "var(--sc-container-max)" }}
    >
      <CounterfactualCard on={on} off={off} />
    </section>
  );
}
