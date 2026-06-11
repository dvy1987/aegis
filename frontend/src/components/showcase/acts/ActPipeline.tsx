"use client";

import { useRef, useState } from "react";
import { useReducedMotion } from "framer-motion";
import { ScrollTrigger, gsap, useGsapContext } from "@/lib/motion";
import { PipelineStage } from "@/components/showcase/fx/PipelineStage";

const sectionClass = "mx-auto w-full scroll-mt-24 px-6 py-24 md:px-12 md:py-32";

/**
 * Pinned pipeline beat — sits directly under GEPA · THE LEARNING LOOP. Scroll
 * scrubs the six stages and callouts (Judge panel, Phoenix memory, GEPA) while
 * the section holds on ≥lg viewports.
 */
export function ActPipeline() {
  const root = useRef<HTMLElement>(null);
  const pin = useRef<HTMLDivElement>(null);
  const [progress, setProgress] = useState(0);
  const reduce = useReducedMotion();

  useGsapContext(
    () => {
      const mm = gsap.matchMedia();

      mm.add("(min-width: 1024px)", () => {
        ScrollTrigger.create({
          trigger: root.current,
          start: "top 5rem",
          end: "+=130%",
          pin: pin.current,
          pinSpacing: true,
          anticipatePin: 1,
          invalidateOnRefresh: true,
          scrub: 0.5,
          onUpdate: (self) => setProgress(self.progress),
        });
      });

      mm.add("(max-width: 1023px)", () => {
        ScrollTrigger.create({
          trigger: root.current,
          start: "top 78%",
          end: "bottom 42%",
          scrub: 0.5,
          onUpdate: (self) => setProgress(self.progress),
        });
      });

      return () => mm.revert();
    },
    { scope: root },
  );

  return (
    <section
      ref={root}
      id="pipeline"
      className={sectionClass}
      style={{ maxWidth: "var(--sc-container-max)" }}
    >
      <div ref={pin}>
        <PipelineStage progress={reduce ? 1 : progress} />
      </div>
    </section>
  );
}
