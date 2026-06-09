"use client";

import { useEffect, useLayoutEffect, useRef } from "react";
import { useReducedMotion } from "framer-motion";
import type { ShowcaseBundle, Verdict } from "@/lib/types";
import { gsap, useGsapContext, useTheatrical } from "@/lib/motion";
import { MonoLabel } from "@/components/showcase/primitives/MonoLabel";
import { GlassPanel } from "@/components/showcase/primitives/GlassPanel";
import {
  VERSUS_DRAFT_AFTER,
  VERSUS_DRAFT_BEFORE,
  VERSUS_ILLUSTRATIVE,
  VERSUS_LIFT_LABEL,
  VERSUS_PHOENIX_LINK,
} from "@/components/showcase/copy";
import { ArrowUpRightIcon } from "@/icons";

const ARC_PATH = "M 16 100 A 84 84 0 0 1 184 100";
const GAUGE_CX = 100;
const GAUGE_CY = 100;

/** Drive arc length + needle from the same point on the path so they stay aligned. */
function setLiftDial(arc: SVGPathElement, needle: SVGGElement, liftRelativePct: number) {
  const t = Math.max(0, Math.min(1, liftRelativePct / 100));
  const len = arc.getTotalLength();
  arc.setAttribute("stroke-dasharray", String(len));
  arc.setAttribute("stroke-dashoffset", String(len * (1 - t)));

  const point = arc.getPointAtLength(len * t);
  const angle = (Math.atan2(point.y - GAUGE_CY, point.x - GAUGE_CX) * 180) / Math.PI;
  // Default needle points up (−90°); rotate to sit on the arc radius.
  needle.setAttribute("transform", `rotate(${angle + 90} ${GAUGE_CX} ${GAUGE_CY})`);
}

/**
 * The page's one symmetric moment — v1 vs v3, with the lift in the middle.
 * A single GSAP timeline fires once on scroll-enter and runs the whole shot in
 * lockstep: left gauge fills, right gauge overtakes, APPROVE lamp blooms, the
 * lift arc draws, the needle springs, and the counters spin — tuned to demo
 * pace. Elements render at their final state so reduced-motion shows the result.
 */
export function VersusPanel({ bundle }: { bundle: ShowcaseBundle }) {
  const root = useRef<HTMLDivElement>(null);
  const needleRef = useRef<SVGGElement>(null);
  const arcRef = useRef<SVGPathElement>(null);
  const reduce = useReducedMotion();
  const { acquire, release } = useTheatrical();
  const theatrical = useRef({ acquire, release });

  useEffect(() => {
    theatrical.current = { acquire, release };
  });

  const v1 = bundle.v1.composite;
  const v3 = bundle.v3.composite;
  const lift = bundle.lift_relative_pct;
  const liftDecimals = lift % 1 === 0 ? 0 : 1;

  useLayoutEffect(() => {
    const arc = arcRef.current;
    const needle = needleRef.current;
    if (!arc || !needle) return;
    setLiftDial(arc, needle, 0);
  }, [bundle.case_id]);

  useLayoutEffect(() => {
    if (!reduce) return;
    const arc = arcRef.current;
    const needle = needleRef.current;
    if (!arc || !needle) return;
    setLiftDial(arc, needle, lift);
  }, [reduce, lift, bundle.case_id]);

  useGsapContext(
    () => {
      const r = root.current;
      const needle = needleRef.current;
      const arc = arcRef.current;
      if (!r || !needle || !arc) return;
      const leftNum = r.querySelector<HTMLElement>(".sc-vs-num-left");
      const rightNum = r.querySelector<HTMLElement>(".sc-vs-num-right");
      const liftNum = r.querySelector<HTMLElement>(".sc-vs-lift");

      gsap.set(".sc-vs-fill-left, .sc-vs-fill-right", { width: 0 });
      gsap.set(".sc-vs-approve-lamp", { boxShadow: "0 0 0 rgba(0,0,0,0)" });
      setLiftDial(arc, needle, 0);

      const c = { l: 0, r: 0, lift: 0 };
      const tl = gsap.timeline({
        paused: true,
        defaults: { ease: "power3.out" },
        onComplete: () => {
          setLiftDial(arc, needle, lift);
          theatrical.current.release("money-shot");
        },
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
        .to(
          c,
          {
            lift,
            duration: 1.1,
            ease: "power2.out",
            onUpdate: () => {
              setLiftDial(arc, needle, c.lift);
              if (liftNum) liftNum.textContent = `+${c.lift.toFixed(liftDecimals)}%`;
            },
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
          title={VERSUS_DRAFT_BEFORE}
          version="v1"
          composite={v1}
          verdict={bundle.v1.verdict}
          excerpt={bundle.v1.letter_excerpt}
        />

        <div className="flex flex-col items-center justify-center gap-2 px-2 py-4">
          <MonoLabel>{VERSUS_LIFT_LABEL}</MonoLabel>
          <svg viewBox="0 0 200 116" className="w-full max-w-[220px]" aria-hidden role="img">
            <path d={ARC_PATH} fill="none" stroke="var(--sc-bg-sunken)" strokeWidth={10} strokeLinecap="round" />
            <path
              ref={arcRef}
              className="sc-vs-arc"
              d={ARC_PATH}
              fill="none"
              stroke="var(--sc-accent)"
              strokeWidth={10}
              strokeLinecap="round"
              style={{ filter: "drop-shadow(0 0 8px var(--sc-accent-glow))" }}
            />
            <g ref={needleRef} className="sc-vs-needle">
              <line
                x1={GAUGE_CX}
                y1={GAUGE_CY}
                x2={GAUGE_CX}
                y2={32}
                stroke="var(--sc-text)"
                strokeWidth={2.5}
                strokeLinecap="round"
              />
            </g>
            <circle cx={GAUGE_CX} cy={GAUGE_CY} r={6} fill="var(--sc-text)" />
          </svg>
          <span
            className="sc-vs-lift sc-c-accent"
            style={{ fontFamily: "var(--font-mono)", fontSize: "2rem", fontWeight: 600 }}
          >
            +{lift.toFixed(liftDecimals)}%
          </span>
        </div>

        <DraftColumn
          title={VERSUS_DRAFT_AFTER}
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
            {VERSUS_ILLUSTRATIVE}
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
            {VERSUS_PHOENIX_LINK}
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
