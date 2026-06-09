"use client";

import { useRef, type ReactNode } from "react";
import { gsap, useGsapContext } from "@/lib/motion";
import { MonoLabel } from "@/components/showcase/primitives/MonoLabel";
import { MetricCounter } from "@/components/showcase/primitives/MetricCounter";
import { LivingGlyph } from "@/components/showcase/fx/LivingGlyph";
import { RiveOrFallback } from "@/components/showcase/fx/RiveOrFallback";
import { IgniteButton } from "@/components/showcase/fx/IgniteButton";

function replay() {
  if (typeof document === "undefined") return;
  document.getElementById("instrument")?.scrollIntoView({ behavior: "smooth", block: "start" });
}

export function ActImpact() {
  const root = useRef<HTMLElement>(null);

  // GSAP finale timeline: headline → glyph settle → metrics (counters fire on
  // their own view) → footer hairline draws → stillness. Triggered on enter.
  useGsapContext(
    () => {
      gsap.set(".sc-im-headline, .sc-im-metric, .sc-im-endcard", { autoAlpha: 0, y: 20 });
      gsap.set(".sc-im-divider", { scaleX: 0, transformOrigin: "left center" });

      gsap
        .timeline({
          defaults: { ease: "power3.out" },
          scrollTrigger: { trigger: root.current, start: "top 70%", once: true },
        })
        .to(".sc-im-headline", { autoAlpha: 1, y: 0, duration: 0.8 })
        .to(".sc-im-metric", { autoAlpha: 1, y: 0, duration: 0.6, stagger: 0.18 }, "-=0.3")
        .to(".sc-im-divider", { scaleX: 1, duration: 0.9, ease: "power2.out" }, "-=0.2")
        .to(".sc-im-endcard", { autoAlpha: 1, y: 0, duration: 0.6 }, "-=0.5");
    },
    { scope: root },
  );

  return (
    <section
      ref={root}
      id="impact"
      className="relative mx-auto flex min-h-dvh w-full flex-col justify-center gap-14 px-6 py-24 md:px-12"
      style={{ maxWidth: "var(--sc-container-max)" }}
    >
      <div className="grid grid-cols-1 items-center gap-12 lg:grid-cols-[1.2fr_0.8fr]">
        <div className="sc-im-headline flex flex-col gap-6">
          <MonoLabel>Why this matters</MonoLabel>
          <h2 className="sc-display" style={{ fontSize: "clamp(2.2rem, 4.5vw, 3.6rem)", maxWidth: "18ch" }}>
            99% of denied claims are never appealed. Aegis keeps getting better at the fight.
          </h2>
        </div>

        <div>
          <RiveOrFallback fallback={<LivingGlyph state="settled" parallax={false} className="mx-auto" />} />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
        <Metric label="Benchmark quality · target">
          <span className="sc-mono" style={{ fontSize: "1.6rem", color: "var(--sc-text-3)" }}>
            0.40&nbsp;→&nbsp;
          </span>
          <MetricCounter
            to={0.75}
            from={0.4}
            decimals={2}
            delay={0.2}
            className="sc-c-accent"
            style={{ fontSize: "1.6rem", fontWeight: 600, letterSpacing: "0" }}
          />
        </Metric>
        <Metric label="Judge dimensions">
          <MetricCounter to={7} delay={0.4} className="sc-c1" style={{ fontSize: "1.6rem", fontWeight: 600, letterSpacing: "0" }} />
        </Metric>
        <Metric label="Human-approved">
          <span className="sc-c1" style={{ fontFamily: "var(--font-mono)", fontSize: "1.6rem", fontWeight: 600 }}>
            ALWAYS
          </span>
        </Metric>
      </div>

      <div className="flex flex-col gap-6">
        <span
          className="sc-im-divider block h-px w-full"
          style={{ background: "var(--sc-accent)", boxShadow: "0 0 10px var(--sc-accent-glow)" }}
        />
        <div className="sc-im-endcard flex flex-wrap items-center justify-between gap-4">
          <MonoLabel style={{ letterSpacing: "0.06em" }}>
            AEGIS · built on Google ADK + Gemini · observability by Arize Phoenix
          </MonoLabel>
          <IgniteButton variant="ghost" onClick={replay}>
            Replay the run
          </IgniteButton>
        </div>
      </div>
    </section>
  );
}

function Metric({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="sc-im-metric flex flex-col gap-2">
      <MonoLabel>{label}</MonoLabel>
      <div className="flex items-baseline">{children}</div>
    </div>
  );
}
