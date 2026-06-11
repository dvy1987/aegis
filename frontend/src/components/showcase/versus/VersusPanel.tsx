"use client";

import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { showcaseSource } from "@/lib/data";
import { isAfterLearningUnlocked } from "@/lib/showcase/simulatorUnlock";
import type {
  CaseSummary,
  ShowcaseBundle,
  ShowcaseMeasureResult,
  ShowcaseMeasureVariant,
  ShowcaseRollbackTarget,
  ShowcaseRunSession,
  Verdict,
} from "@/lib/types";
import { cn } from "@/lib/cn";
import { gsap, useGsapContext, useTheatrical } from "@/lib/motion";
import { MonoLabel } from "@/components/showcase/primitives/MonoLabel";
import { GlassPanel } from "@/components/showcase/primitives/GlassPanel";
import {
  SIMULATOR_MODAL_EYEBROW,
  VERSUS_AFTER_LOCKED,
  VERSUS_DRAFT_MODAL_EYEBROW,
  VERSUS_DRAFT_AFTER,
  VERSUS_DRAFT_BEFORE,
  VERSUS_ILLUSTRATIVE,
  VERSUS_LIFT_LABEL,
  VERSUS_PENDING,
  VERSUS_PHOENIX_LINK,
  VERSUS_RUN_SIMULATOR,
  VERSUS_VIEW_DRAFT,
} from "@/components/showcase/copy";
import { ArrowUpRightIcon } from "@/icons";
import { CaseDocumentModal } from "./CaseDocumentModal";
import { SimulatorResultModal } from "./SimulatorResultModal";

const ARC_PATH = "M 16 100 A 84 84 0 0 1 184 100";
const GAUGE_CX = 100;
const GAUGE_CY = 100;

type RunCache = Partial<Record<ShowcaseMeasureVariant, ShowcaseMeasureResult>>;

function setLiftDial(arc: SVGPathElement, needle: SVGGElement, liftRelativePct: number) {
  const t = Math.max(0, Math.min(1, liftRelativePct / 100));
  const len = arc.getTotalLength();
  arc.setAttribute("stroke-dasharray", String(len));
  arc.setAttribute("stroke-dashoffset", String(len * (1 - t)));

  const point = arc.getPointAtLength(len * t);
  const angle = (Math.atan2(point.y - GAUGE_CY, point.x - GAUGE_CX) * 180) / Math.PI;
  needle.setAttribute("transform", `rotate(${angle + 90} ${GAUGE_CX} ${GAUGE_CY})`);
}

export function VersusPanel({
  bundle,
  caseSummary,
  runSession,
  rollbackTarget,
}: {
  bundle: ShowcaseBundle;
  caseSummary: CaseSummary;
  runSession: ShowcaseRunSession | null;
  rollbackTarget: ShowcaseRollbackTarget | null;
}) {
  const root = useRef<HTMLDivElement>(null);
  const needleRef = useRef<SVGGElement>(null);
  const arcRef = useRef<SVGPathElement>(null);
  const { acquire, release } = useTheatrical();
  const theatrical = useRef({ acquire, release });

  const afterUnlocked = isAfterLearningUnlocked(runSession, rollbackTarget);
  const [runs, setRuns] = useState<Record<string, RunCache>>({});
  const [loading, setLoading] = useState<ShowcaseMeasureVariant | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [draftModal, setDraftModal] = useState<ShowcaseMeasureVariant | null>(null);
  const [simModal, setSimModal] = useState<ShowcaseMeasureResult | null>(null);

  const cache = runs[bundle.case_id] ?? {};
  const measured = bundle.measured;
  const v1 = measured ? bundle.v1.composite : 0;
  const v3 = measured ? bundle.v3.composite : 0;
  const lift = measured ? bundle.lift_relative_pct : 0;
  const liftDecimals = lift % 1 === 0 ? 0 : 1;

  useEffect(() => {
    theatrical.current = { acquire, release };
  });

  useEffect(() => {
    setError(null);
    setDraftModal(null);
    setSimModal(null);
  }, [bundle.case_id]);

  const sideFromBundle = (variant: ShowcaseMeasureVariant) =>
    variant === "baseline" ? bundle.v1 : bundle.v3;

  const resolveSide = (variant: ShowcaseMeasureVariant) => {
    const run = cache[variant];
    const side = sideFromBundle(variant);
    return {
      composite: measured ? (run?.score ?? side.composite) : 0,
      verdict: (measured ? (run?.verdict ?? side.verdict) : "DENY") as Verdict,
      excerpt: run?.letter_excerpt || side.letter_excerpt,
      letter: run?.appeal_letter ?? "",
    };
  };

  async function fetchMeasure(variant: ShowcaseMeasureVariant): Promise<ShowcaseMeasureResult> {
    const cached = cache[variant];
    if (cached) return cached;
    const result = await showcaseSource.runShowcaseMeasure(caseSummary, variant);
    setRuns((prev) => ({
      ...prev,
      [bundle.case_id]: { ...prev[bundle.case_id], [variant]: result },
    }));
    return result;
  }

  const runSimulator = async (variant: ShowcaseMeasureVariant) => {
    setLoading(variant);
    setError(null);
    try {
      const result = await fetchMeasure(variant);
      setSimModal(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(null);
    }
  };

  const openDraft = async (variant: ShowcaseMeasureVariant) => {
    setLoading(variant);
    setError(null);
    try {
      const cached = cache[variant];
      if (cached?.appeal_letter) {
        setDraftModal(variant);
        return;
      }
      const excerpt = sideFromBundle(variant).letter_excerpt;
      if (excerpt) {
        setDraftModal(variant);
        return;
      }
      await fetchMeasure(variant);
      setDraftModal(variant);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(null);
    }
  };

  const baseline = resolveSide("baseline");
  const candidate = resolveSide("candidate");
  const draftBody =
    draftModal === "baseline"
      ? cache.baseline?.appeal_letter || bundle.v1.letter_excerpt
      : draftModal === "candidate"
        ? cache.candidate?.appeal_letter || bundle.v3.letter_excerpt
        : "";

  useLayoutEffect(() => {
    const arc = arcRef.current;
    const needle = needleRef.current;
    if (!arc || !needle) return;
    setLiftDial(arc, needle, lift);
  }, [bundle.case_id, lift]);

  useGsapContext(
    () => {
      if (!measured) return;

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
    { scope: root, dependencies: [bundle.case_id, measured] },
  );

  return (
    <>
      <div ref={root} data-theatrical-zone="money-shot" className="flex flex-col gap-6">
        <div className="grid grid-cols-1 items-stretch gap-5 lg:grid-cols-[1fr_auto_1fr]">
          <DraftColumn
            title={VERSUS_DRAFT_BEFORE}
            version="v1"
            composite={baseline.composite}
            verdict={baseline.verdict}
            inactive={!measured}
            actionsLocked={false}
            loading={loading === "baseline"}
            onRunSimulator={() => void runSimulator("baseline")}
            onViewDraft={() => void openDraft("baseline")}
          />

          <div
            className="flex flex-col items-center justify-center gap-2 px-2 py-4"
            style={!measured ? { opacity: 0.55 } : undefined}
          >
            <MonoLabel>{VERSUS_LIFT_LABEL}</MonoLabel>
            <svg viewBox="0 0 200 116" className="w-full max-w-[220px]" aria-hidden role="img">
              <path d={ARC_PATH} fill="none" stroke="var(--sc-bg-sunken)" strokeWidth={10} strokeLinecap="round" />
              <path
                ref={arcRef}
                className="sc-vs-arc"
                d={ARC_PATH}
                fill="none"
                stroke={measured ? "var(--sc-accent)" : "var(--sc-text-3)"}
                strokeWidth={10}
                strokeLinecap="round"
                style={measured ? { filter: "drop-shadow(0 0 8px var(--sc-accent-glow))" } : undefined}
              />
              <g ref={needleRef} className="sc-vs-needle">
                <line
                  x1={GAUGE_CX}
                  y1={GAUGE_CY}
                  x2={GAUGE_CX}
                  y2={32}
                  stroke={measured ? "var(--sc-text)" : "var(--sc-text-3)"}
                  strokeWidth={2.5}
                  strokeLinecap="round"
                />
              </g>
              <circle cx={GAUGE_CX} cy={GAUGE_CY} r={6} fill={measured ? "var(--sc-text)" : "var(--sc-text-3)"} />
            </svg>
            <span
              className={measured ? "sc-vs-lift sc-c-accent" : "sc-vs-lift"}
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "2rem",
                fontWeight: 600,
                color: measured ? undefined : "var(--sc-text-3)",
              }}
            >
              {measured ? `+${lift.toFixed(liftDecimals)}%` : "0%"}
            </span>
          </div>

          <DraftColumn
            title={VERSUS_DRAFT_AFTER}
            version="v3"
            composite={candidate.composite}
            verdict={candidate.verdict}
            improved
            inactive={!measured}
            actionsLocked={!afterUnlocked}
            lockedHint={VERSUS_AFTER_LOCKED}
            loading={loading === "candidate"}
            onRunSimulator={() => void runSimulator("candidate")}
            onViewDraft={() => void openDraft("candidate")}
          />
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3">
          {error && (
            <p className="sc-mono" style={{ color: "var(--sc-deny)" }}>
              {error}
            </p>
          )}
          {!error && !measured && (
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

      <CaseDocumentModal
        open={draftModal !== null}
        title={draftModal === "baseline" ? VERSUS_DRAFT_BEFORE : VERSUS_DRAFT_AFTER}
        eyebrow={VERSUS_DRAFT_MODAL_EYEBROW}
        body={draftBody}
        onClose={() => setDraftModal(null)}
      />

      <SimulatorResultModal
        open={simModal !== null}
        result={simModal}
        title={simModal?.variant === "baseline" ? VERSUS_DRAFT_BEFORE : VERSUS_DRAFT_AFTER}
        onClose={() => setSimModal(null)}
      />
    </>
  );
}

function DraftColumn({
  title,
  version,
  composite,
  verdict,
  improved = false,
  inactive = false,
  actionsLocked = false,
  lockedHint,
  loading = false,
  onRunSimulator,
  onViewDraft,
}: {
  title: string;
  version: string;
  composite: number;
  verdict: Verdict;
  improved?: boolean;
  inactive?: boolean;
  actionsLocked?: boolean;
  lockedHint?: string;
  loading?: boolean;
  onRunSimulator: () => void;
  onViewDraft: () => void;
}) {
  const side = improved ? "right" : "left";
  const tone = inactive ? "var(--sc-text-3)" : improved ? "var(--sc-accent)" : "var(--sc-deny)";
  const verdictLabel = inactive ? VERSUS_PENDING : verdict === "APPROVE" ? "SIMULATOR · APPROVE" : "SIMULATOR · DENY";
  const hasLiveData = !inactive;

  return (
    <GlassPanel
      variant={inactive ? "default" : improved ? "active" : "default"}
      className="flex flex-col gap-4 p-6 transition-[opacity,filter]"
      style={
        inactive
          ? {
              opacity: 0.52,
              filter: "saturate(0.25)",
              borderColor: "var(--sc-hairline)",
            }
          : undefined
      }
    >
      <div className="flex items-center justify-between gap-3">
        <div className="flex flex-col">
          <MonoLabel>{version}</MonoLabel>
          <span
            className="sc-serif"
            style={{ color: inactive ? "var(--sc-text-3)" : "var(--sc-text)", fontSize: "1.15rem" }}
          >
            {title}
          </span>
        </div>
        <span
          className={
            improved && !inactive
              ? "sc-vs-approve-lamp inline-flex items-center gap-2 rounded-full px-3 py-1"
              : "inline-flex items-center gap-2 rounded-full px-3 py-1"
          }
          style={{ border: `1px solid ${tone}`, color: tone }}
        >
          <span
            className="h-2 w-2 rounded-full"
            style={{
              background: tone,
              boxShadow: inactive ? "none" : `0 0 8px ${tone}`,
            }}
          />
          <span className="sc-mono" style={{ color: tone, fontSize: inactive ? "0.7rem" : undefined }}>
            {verdictLabel}
          </span>
        </span>
      </div>

      <div className="flex flex-col gap-2">
        <MonoLabel>Composite quality</MonoLabel>
        <div className="relative h-2 w-full overflow-hidden rounded-full" style={{ background: "var(--sc-bg-sunken)" }}>
          <div
            className={side === "right" ? "sc-vs-fill-right h-full rounded-full" : "sc-vs-fill-left h-full rounded-full"}
            style={{
              width: inactive && composite === 0 ? "0%" : `${composite * 100}%`,
              background: tone,
              boxShadow: inactive && composite === 0 ? "none" : `0 0 12px ${tone}`,
            }}
          />
        </div>
        <span
          className={side === "right" ? "sc-vs-num-right sc-mono" : "sc-vs-num-left sc-mono"}
          style={{ color: "var(--sc-text-3)" }}
        >
          {inactive && composite === 0 ? "—" : composite.toFixed(2)}
        </span>
      </div>

      <div className="flex flex-col gap-2">
        <div className="flex flex-wrap gap-2">
          <ActionButton
            label={loading ? "Running…" : VERSUS_RUN_SIMULATOR}
            onClick={onRunSimulator}
            disabled={actionsLocked || loading}
            muted={actionsLocked}
          />
          <ActionButton
            label={VERSUS_VIEW_DRAFT}
            onClick={onViewDraft}
            disabled={actionsLocked || loading}
            muted={actionsLocked}
            variant="secondary"
          />
        </div>
        {actionsLocked && lockedHint && (
          <p className="sc-mono" style={{ color: "var(--sc-text-3)", fontSize: "0.72rem" }}>
            {lockedHint}
          </p>
        )}
        {hasLiveData && !actionsLocked && (
          <p className="sc-mono" style={{ color: "var(--sc-text-3)", fontSize: "0.72rem" }}>
            {SIMULATOR_MODAL_EYEBROW} · live drafter + proxy review
          </p>
        )}
      </div>
    </GlassPanel>
  );
}

function ActionButton({
  label,
  onClick,
  disabled,
  muted,
  variant = "primary",
}: {
  label: string;
  onClick: () => void;
  disabled?: boolean;
  muted?: boolean;
  variant?: "primary" | "secondary";
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "rounded-full px-3 py-1.5 sc-mono transition-colors focus-visible:outline-2 focus-visible:outline-offset-2",
        muted && "cursor-not-allowed",
      )}
      style={{
        border: `1px solid ${muted || disabled ? "var(--sc-hairline)" : variant === "primary" ? "var(--sc-accent)" : "var(--sc-hairline-strong)"}`,
        color: muted || disabled ? "var(--sc-text-3)" : variant === "primary" ? "var(--sc-accent)" : "var(--sc-text-2)",
        background:
          muted || disabled
            ? "transparent"
            : variant === "primary"
              ? "color-mix(in oklch, var(--sc-accent) 10%, transparent)"
              : "transparent",
        opacity: muted ? 0.55 : disabled ? 0.7 : 1,
        outlineColor: "var(--sc-accent)",
      }}
    >
      {label}
    </button>
  );
}
