"use client";

import { useEffect, useRef } from "react";
import type { ShowcaseBundle, Verdict } from "@/lib/types";
import { gsap, useGsapContext, useTheatrical } from "@/lib/motion";
import { MonoLabel } from "@/components/showcase/primitives/MonoLabel";
import { GlassPanel } from "@/components/showcase/primitives/GlassPanel";
import { ArrowUpRightIcon } from "@/icons";

const ARC_LEN = Math.PI * 84; // semicircle r=84

/**
 * The page's one symmetric moment — v1 vs v3, with the lift in the middle.
 * A single GSAP timeline fires once on scroll-enter and runs the whole shot in
 * lockstep: left gauge fills, right gauge overtakes, APPROVE lamp blooms, the
 * lift arc draws, the needle springs, and the counters spin — tuned to demo
 * pace. Elements render at their final state so reduced-motion shows the result.
 */
export function VersusPanel({ bundle }: { bundle: ShowcaseBundle }) {
  const root = useRef<HTMLDivElement>(null);
  const { acquire, release } = useTheatrical();
  const theatrical = useRef({ acquire, release });

  useEffect(() => {
    theatrical.current = { acquire, release };
  });

  const v1 = bundle.v1.composite;
  const v3 = bundle.v3.composite;
  const lift = bundle.lift_relative_pct;
  const liftFrac = Math.max(0, Math.min(1, lift / 100));
  const liftAngle = -90 + liftFrac * 180;
  const liftDecimals = lift % 1 === 0 ? 0 : 1;

  useGsapContext(
    () => {
      const r = root.current;
      if (!r) return;
      const leftNum = r.querySelector<HTMLElement>(".sc-vs-num-left");
      const rightNum = r.querySelector<HTMLElement>(".sc-vs-num-right");
      const liftNum = r.querySelector<HTMLElement>(".sc-vs-lift");

      gsap.set(".sc-vs-fill-left, .sc-vs-fill-right", { width: 0 });
      gsap.set(".sc-vs-approve-lamp", { boxShadow: "0 0 0 rgba(0,0,0,0)" });
      gsap.set(".sc-vs-arc", { strokeDashoffset: ARC_LEN });
      gsap.set(".sc-vs-needle", { rotation: -90, svgOrigin: "100 100" });

      const c = { l: 0, r: 0, lift: 0 };
      const tl = gsap.timeline({
        paused: true,
        defaults: { ease: "power3.out" },
        onComplete: () => theatrical.current.release("money-shot"),
      });

      tl.to(".sc-vs-fill-left", { width: `${v1 * 100}%`, duration: 0.9 }, 0)
        .to(
          c,
          { l: v1, duration: 0.9, onUpdate: () => leftNum && (leftNum.textContent = c.l.toFixed(2)) },
          0,
        )
        .to(".sc-vs-fill-right", { width: `${v3 * 100}%`, duration: 1.0 }, 0.5)
        .to(
          c,
          { r: v3, duration: 1.0, onUpdate: () => rightNum && (rightNum.textContent = c.r.toFixed(2)) },
          0.5,
        )
        .to(".sc-vs-approve-lamp", { boxShadow: "0 0 26px var(--sc-accent-glow)", duration: 0.6 }, 1.0)
        .to(".sc-vs-arc", { strokeDashoffset: ARC_LEN * (1 - liftFrac), duration: 1.1, ease: "power2.out" }, 0.9)
        .to(".sc-vs-needle", { rotation: liftAngle, svgOrigin: "100 100", duration: 1.1, ease: "back.out(1.4)" }, 0.9)
        .to(
          c,
          {
            lift,
            duration: 1.1,
            onUpdate: () => liftNum && (liftNum.textContent = `+${c.lift.toFixed(liftDecimals)}%`),
          },
          0.9,
        );

      gsap.timeline({
        scrollTrigger: {
          trigger: r,
          start: "top 78%",
          once: true,
          onEnter: () => {
            void theatrical.current.acquire("money-shot").then(() => tl.play());
          },
        },
      });
    },
    { scope: root, dependencies: [bundle.case_id] },
  );

  return (
    <div ref={root} data-theatrical-zone="money-shot" className="flex flex-col gap-6">
      <div className="grid grid-cols-1 items-stretch gap-5 lg:grid-cols-[1fr_auto_1fr]">
        <DraftColumn
          title="Earlier draft"
          version="v1"
          composite={v1}
          verdict={bundle.v1.verdict}
          excerpt={bundle.v1.letter_excerpt}
        />

        <div className="flex flex-col items-center justify-center gap-2 px-2 py-4">
          <MonoLabel>Measured lift · held-out</MonoLabel>
          <svg viewBox="0 0 200 116" className="w-full max-w-[220px]" aria-hidden role="img">
            <path d="M 16 100 A 84 84 0 0 1 184 100" fill="none" stroke="var(--sc-bg-sunken)" strokeWidth={10} strokeLinecap="round" />
            <path
              className="sc-vs-arc"
              d="M 16 100 A 84 84 0 0 1 184 100"
              fill="none"
              stroke="var(--sc-accent)"
              strokeWidth={10}
              strokeLinecap="round"
              strokeDasharray={ARC_LEN}
              strokeDashoffset={ARC_LEN * (1 - liftFrac)}
              style={{ filter: "drop-shadow(0 0 8px var(--sc-accent-glow))" }}
            />
            <g className="sc-vs-needle" style={{ transform: `rotate(${liftAngle}deg)`, transformOrigin: "100px 100px" }}>
              <line x1={100} y1={100} x2={100} y2={32} stroke="var(--sc-text)" strokeWidth={2.5} strokeLinecap="round" />
            </g>
            <circle cx={100} cy={100} r={6} fill="var(--sc-text)" />
          </svg>
          <span
            className="sc-vs-lift sc-c-accent"
            style={{ fontFamily: "var(--font-mono)", fontSize: "2rem", fontWeight: 600 }}
          >
            +{lift.toFixed(liftDecimals)}%
          </span>
        </div>

        <DraftColumn
          title="Improved draft"
          version="v3"
          composite={v3}
          verdict={bundle.v3.verdict}
          excerpt={bundle.v3.letter_excerpt}
          improved
        />
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        {!bundle.measured && (
          <p className="sc-mono" style={{ color: "var(--sc-text-3)" }}>
            Illustrative for this case. Measured numbers shown where a run is recorded.
          </p>
        )}
        {bundle.phoenix_url && (
          <a
            href={bundle.phoenix_url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 sc-mono transition-colors hover:opacity-80"
            style={{ color: "var(--sc-accent)" }}
          >
            INSPECT THE UNDERLYING TRACE
            <ArrowUpRightIcon size={16} />
          </a>
        )}
      </div>
    </div>
  );
}

function DraftColumn({
  title,
  version,
  composite,
  verdict,
  excerpt,
  improved = false,
}: {
  title: string;
  version: string;
  composite: number;
  verdict: Verdict;
  excerpt: string;
  improved?: boolean;
}) {
  const side = improved ? "right" : "left";
  const tone = improved ? "var(--sc-accent)" : "var(--sc-deny)";
  return (
    <GlassPanel variant={improved ? "active" : "default"} className="flex flex-col gap-4 p-6">
      <div className="flex items-center justify-between gap-3">
        <div className="flex flex-col">
          <MonoLabel>{version}</MonoLabel>
          <span className="sc-serif" style={{ color: "var(--sc-text)", fontSize: "1.15rem" }}>
            {title}
          </span>
        </div>
        <span
          className={improved ? "sc-vs-approve-lamp inline-flex items-center gap-2 rounded-full px-3 py-1" : "inline-flex items-center gap-2 rounded-full px-3 py-1"}
          style={{ border: `1px solid ${tone}`, color: tone }}
        >
          <span className="h-2 w-2 rounded-full" style={{ background: tone, boxShadow: `0 0 8px ${tone}` }} />
          <span className="sc-mono" style={{ color: tone }}>
            {verdict === "APPROVE" ? "SIMULATOR · APPROVE" : "SIMULATOR · DENY"}
          </span>
        </span>
      </div>

      <div className="flex flex-col gap-2">
        <MonoLabel>Composite quality</MonoLabel>
        <div className="relative h-2 w-full overflow-hidden rounded-full" style={{ background: "var(--sc-bg-sunken)" }}>
          <div
            className={side === "right" ? "sc-vs-fill-right h-full rounded-full" : "sc-vs-fill-left h-full rounded-full"}
            style={{ width: `${composite * 100}%`, background: tone, boxShadow: `0 0 12px ${tone}` }}
          />
        </div>
        <span className={side === "right" ? "sc-vs-num-right sc-mono" : "sc-vs-num-left sc-mono"} style={{ color: "var(--sc-text-3)" }}>
          {composite.toFixed(2)}
        </span>
      </div>

      <p
        className="sc-body rounded-md p-4"
        style={{ fontSize: "0.9rem", color: "var(--sc-text-2)", background: "var(--sc-bg-sunken)", border: "1px solid var(--sc-hairline)" }}
      >
        {excerpt}
      </p>
    </GlassPanel>
  );
}
