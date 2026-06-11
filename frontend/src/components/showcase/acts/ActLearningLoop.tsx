"use client";

import { useRef } from "react";
import { motion } from "framer-motion";
import { EASE_OUT_EXPO, gsap, useGsapContext } from "@/lib/motion";
import { MonoLabel } from "@/components/showcase/primitives/MonoLabel";
import { GepaSpotlight } from "@/components/showcase/acts/GepaSpotlight";
import {
  INTELLIGENCE_BODY,
  INTELLIGENCE_EYEBROW,
  INTELLIGENCE_HEADLINE,
} from "@/components/showcase/copy";

const sectionClass =
  "mx-auto w-full scroll-mt-24 px-6 py-24 md:px-12 md:py-32";

/**
 * GEPA learning-loop beat — pinned on ≥lg so the section holds while the user
 * scrolls through the intro and spotlight, matching the LIVE LEARNING CONSOLE.
 */
export function ActLearningLoop() {
  const root = useRef<HTMLElement>(null);
  const pin = useRef<HTMLDivElement>(null);

  useGsapContext(
    () => {
      const mm = gsap.matchMedia();
      mm.add("(min-width: 1024px)", () => {
        gsap.timeline({
          scrollTrigger: {
            trigger: root.current,
            start: "top 5rem",
            end: "+=100%",
            pin: pin.current,
            pinSpacing: true,
            anticipatePin: 1,
            invalidateOnRefresh: true,
          },
        });
      });
      return () => mm.revert();
    },
    { scope: root },
  );

  return (
    <section
      ref={root}
      id="learning-loop"
      className={sectionClass}
      style={{ maxWidth: "var(--sc-container-max)" }}
    >
      <div ref={pin} className="flex flex-col gap-14">
        <motion.div
          className="flex flex-col gap-2"
          initial={{ opacity: 0, y: 16, filter: "blur(8px)" }}
          whileInView={{ opacity: 1, y: 0, filter: "blur(0px)" }}
          viewport={{ once: true, amount: 0.6 }}
          transition={{ duration: 0.6, ease: EASE_OUT_EXPO }}
        >
          <MonoLabel>{INTELLIGENCE_EYEBROW}</MonoLabel>
          <h2 className="sc-h2">{INTELLIGENCE_HEADLINE}</h2>
          <p className="max-w-prose sc-body">{INTELLIGENCE_BODY}</p>
        </motion.div>

        <GepaSpotlight />
      </div>
    </section>
  );
}
