"use client";

import { useEffect, useRef, useState } from "react";
import { useReducedMotion } from "framer-motion";
import { gsap, useGsapContext, useTheatrical } from "@/lib/motion";
import { MonoLabel } from "@/components/showcase/primitives/MonoLabel";
import { IgniteButton } from "@/components/showcase/fx/IgniteButton";
import { LivingGlyph } from "@/components/showcase/fx/LivingGlyph";
import { RiveOrFallback } from "@/components/showcase/fx/RiveOrFallback";

const HEADLINE = ["Watch", "a", "system", "teach", "itself."];

const TELEMETRY = [
  "SESSION 0x… · STAGE measure_before · 14/20",
  "JUDGE J3 grounding 0.62 → 0.81",
  "PHOENIX trace ingested · 312 spans",
  "GEPA candidate proposed · awaiting approval",
  "HOLD-OUT composite 0.40 → 0.75 (target)",
];

function scrollToInstrument() {
  if (typeof document === "undefined") return;
  document.getElementById("instrument")?.scrollIntoView({ behavior: "smooth", block: "start" });
}

export function ActHero() {
  const reduce = useReducedMotion();
  const root = useRef<HTMLElement>(null);
  const { acquire, release } = useTheatrical();
  const theatrical = useRef({ acquire, release });
  const [glyphState, setGlyphState] = useState<"ignite" | "idle">(reduce ? "idle" : "ignite");

  useEffect(() => {
    theatrical.current = { acquire, release };
  });

  useEffect(() => {
    if (reduce) return;
    const t = window.setTimeout(() => setGlyphState("idle"), 1700);
    return () => window.clearTimeout(t);
  }, [reduce]);

  // GSAP ignition timeline (owns all hero text). Reduced-motion: skipped by the
  // hook, so elements render at their final, visible state.
  useGsapContext(
    () => {
      void theatrical.current.acquire("hero");

      gsap.set(".sc-hero-eyebrow, .sc-hero-sub, .sc-hero-cta", { autoAlpha: 0, y: 16 });
      gsap.set(".sc-hero-word", { autoAlpha: 0, yPercent: 64, filter: "blur(10px)" });
      gsap.set(".sc-hero-telemetry", { autoAlpha: 0 });

      const tl = gsap.timeline({
        defaults: { ease: "power3.out" },
        onComplete: () => theatrical.current.release("hero"),
      });
      tl.to(".sc-hero-eyebrow", { autoAlpha: 1, y: 0, duration: 0.6 }, 0.15)
        .to(
          ".sc-hero-word",
          { autoAlpha: 1, yPercent: 0, filter: "blur(0px)", duration: 0.75, stagger: 0.08 },
          0.3,
        )
        .to(".sc-hero-sub", { autoAlpha: 1, y: 0, duration: 0.6 }, "-=0.3")
        .to(".sc-hero-cta", { autoAlpha: 1, y: 0, duration: 0.5 }, "-=0.35")
        .to(".sc-hero-telemetry", { autoAlpha: 1, duration: 0.6 }, "-=0.3");

      // Glyph drifts up + fades as the hero scrolls away (scrubbed).
      gsap.to(".sc-hero-glyph", {
        yPercent: -14,
        autoAlpha: 0.35,
        ease: "none",
        scrollTrigger: {
          trigger: root.current,
          start: "top top",
          end: "bottom top",
          scrub: true,
        },
      });
    },
    { scope: root },
  );

  return (
    <section
      ref={root}
      id="hero"
      data-theatrical-zone="hero"
      className="relative mx-auto flex min-h-dvh w-full flex-col justify-center px-6 py-24 md:px-12"
      style={{ maxWidth: "var(--sc-container-max)" }}
    >
      <div className="grid grid-cols-1 items-center gap-12 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="flex flex-col gap-6">
          <div className="sc-hero-eyebrow">
            <MonoLabel>AEGIS · SELF-IMPROVING APPEAL ENGINE</MonoLabel>
          </div>

          <h1 className="sc-display" style={{ maxWidth: "16ch" }}>
            {HEADLINE.map((word, i) => (
              <span key={i} className="sc-hero-word inline-block" style={{ marginRight: "0.25em" }}>
                {word}
              </span>
            ))}
          </h1>

          <p className="sc-hero-sub max-w-prose sc-body" style={{ fontSize: "1.15rem" }}>
            Aegis drafts insurance-denial appeals, grades its own work against a held-out benchmark,
            and rewrites its own playbook from what it learns. No hand-tuning. Below, it does it live.
          </p>

          <div className="sc-hero-cta">
            <IgniteButton variant="primary" onClick={scrollToInstrument}>
              Begin a live run
            </IgniteButton>
          </div>
        </div>

        <div className="sc-hero-glyph order-first lg:order-last">
          <RiveOrFallback fallback={<LivingGlyph state={glyphState} className="mx-auto" />} />
        </div>
      </div>

      <TelemetryStrip />
    </section>
  );
}

function TelemetryStrip() {
  const reduce = useReducedMotion();
  const [i, setI] = useState(0);
  useEffect(() => {
    if (reduce) return;
    const t = window.setInterval(() => setI((n) => (n + 1) % TELEMETRY.length), 2600);
    return () => window.clearInterval(t);
  }, [reduce]);

  return (
    <div className="sc-hero-telemetry mt-16 flex items-center gap-3" aria-hidden>
      <span className="h-1.5 w-1.5 rounded-full sc-pulse-soft" style={{ background: "var(--sc-accent)" }} />
      <span className="sc-mono">{TELEMETRY[i]}</span>
      <span className="sc-mono sc-blink">▌</span>
    </div>
  );
}
