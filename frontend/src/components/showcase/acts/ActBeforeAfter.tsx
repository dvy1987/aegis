"use client";

import { useEffect, useRef } from "react";
import { motion, useReducedMotion } from "framer-motion";
import type {
  CaseSummary,
  MeasuredLiftCache,
  ShowcaseBundle,
  ShowcaseMeasureResult,
  ShowcaseMeasureVariant,
  ShowcaseRollbackTarget,
  ShowcaseRunSession,
} from "@/lib/types";
import { EASE_OUT_EXPO, ScrollTrigger, gsap, useGsapContext } from "@/lib/motion";
import { MonoLabel } from "@/components/showcase/primitives/MonoLabel";
import { CaseCycler } from "@/components/showcase/versus/CaseCycler";
import { VersusPanel } from "@/components/showcase/versus/VersusPanel";
import { BEFORE_AFTER_EYEBROW, BEFORE_AFTER_HEADLINE } from "@/components/showcase/copy";
import { DiffCard } from "@/components/showcase/versus/DiffCard";

const sectionClass = "mx-auto w-full scroll-mt-24 px-6 py-24 md:px-12 md:py-32";
const PIN_TOP_OFFSET_PX = 80; // matches start: "top 5rem"

function pinScrollDistance(pinEl: HTMLElement | null) {
  if (!pinEl) return window.innerHeight * 0.5;
  const viewable = window.innerHeight - PIN_TOP_OFFSET_PX;
  const excess = Math.max(0, pinEl.offsetHeight - viewable);
  return Math.max(excess, window.innerHeight * 0.45);
}

/**
 * Act IV — measured lift. Headline, cycler, versus, and diff pin together on ≥lg.
 * Tall content scrolls through as one unit (scrubbed translate) so nothing detaches
 * and the memory section below gets correct pin spacing.
 */
export function ActBeforeAfter({
  bundle,
  cases,
  selected,
  onSelect,
  previewSession,
  productionSession,
  measuredLift,
  onMeasuredLiftUpdate,
  rollbackTarget,
}: {
  bundle: ShowcaseBundle | null;
  cases: CaseSummary[];
  selected: string;
  onSelect: (id: string) => void;
  previewSession: ShowcaseRunSession | null;
  productionSession: ShowcaseRunSession | null;
  measuredLift: MeasuredLiftCache;
  onMeasuredLiftUpdate: (
    caseId: string,
    variant: ShowcaseMeasureVariant,
    result: ShowcaseMeasureResult,
  ) => void;
  rollbackTarget: ShowcaseRollbackTarget | null;
}) {
  const root = useRef<HTMLElement>(null);
  const pin = useRef<HTMLDivElement>(null);
  const pinContent = useRef<HTMLDivElement>(null);
  const reduce = useReducedMotion();
  const currentCase = cases.find((c) => c.case_id === selected) ?? cases[0];

  useGsapContext(
    () => {
      const mm = gsap.matchMedia();
      mm.add("(min-width: 1024px)", () => {
        const content = pinContent.current;
        const viewable = () => window.innerHeight - PIN_TOP_OFFSET_PX;
        const excess = () =>
          Math.max(0, (content?.offsetHeight ?? 0) - viewable());

        const tl = gsap.timeline({
          scrollTrigger: {
            trigger: root.current,
            start: "top 5rem",
            end: () => `+=${pinScrollDistance(content)}`,
            pin: pin.current,
            pinSpacing: true,
            scrub: 0.5,
            anticipatePin: 1,
            invalidateOnRefresh: true,
          },
        });

        if (content && excess() > 0) {
          tl.to(content, { y: -excess(), ease: "none" }, 0);
        }
      });
      return () => mm.revert();
    },
    { scope: root },
  );

  useEffect(() => {
    if (reduce) return;
    const refresh = () => ScrollTrigger.refresh();
    const id = window.requestAnimationFrame(refresh);
    const t = window.setTimeout(refresh, 120);
    return () => {
      window.cancelAnimationFrame(id);
      window.clearTimeout(t);
    };
  }, [bundle?.case_id, bundle?.measured, cases.length, reduce]);

  return (
    <section
      ref={root}
      id="before-after"
      className={sectionClass}
      style={{ maxWidth: "var(--sc-container-max)" }}
    >
      <div ref={pin} className="overflow-hidden lg:max-h-[calc(100dvh-5rem)]">
        <div ref={pinContent} className="flex flex-col gap-10">
          <motion.div
            className="flex flex-col gap-2"
            initial={{ opacity: 0, y: 16, filter: "blur(8px)" }}
            whileInView={{ opacity: 1, y: 0, filter: "blur(0px)" }}
            viewport={{ once: true, amount: 0.6 }}
            transition={{ duration: 0.6, ease: EASE_OUT_EXPO }}
          >
            <MonoLabel>{BEFORE_AFTER_EYEBROW}</MonoLabel>
            <h2 className="sc-h2">{BEFORE_AFTER_HEADLINE}</h2>
          </motion.div>

          <CaseCycler cases={cases} selected={selected} onSelect={onSelect} />

          {bundle && currentCase && (
            <>
              <VersusPanel
                key={`versus-${bundle.case_id}`}
                bundle={bundle}
                caseSummary={currentCase}
                previewSession={previewSession}
                productionSession={productionSession}
                measuredLift={measuredLift}
                onMeasuredLiftUpdate={onMeasuredLiftUpdate}
                rollbackTarget={rollbackTarget}
                sectionRef={root}
              />
              {bundle.measured && (
                <DiffCard key={`diff-${bundle.case_id}`} whatChanged={bundle.what_changed} />
              )}
            </>
          )}
        </div>
      </div>
    </section>
  );
}
