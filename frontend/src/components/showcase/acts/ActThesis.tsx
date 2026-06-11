"use client";

import { useRef, type ReactNode } from "react";
import { gsap, useGsapContext } from "@/lib/motion";
import {
  THESIS_HEURISTICS_CAPTION,
  THESIS_HEURISTICS_LABEL,
  THESIS_FORESHADOW,
  THESIS_STATIC_CAPTION,
  THESIS_STATIC_LABEL,
  THESIS_STATEMENT,
  THESIS_TURN,
} from "@/components/showcase/copy";
import { MonoLabel } from "@/components/showcase/primitives/MonoLabel";

/**
 * The thesis beat. On ≥lg it is a true GSAP ScrollTrigger pin + scrub: the page
 * holds while the statement, the turn, the two nodes, and "learns" resolve in
 * sequence. On smaller screens / reduced-motion it degrades to a static layout
 * (elements render visible; the GSAP setup is skipped).
 */
export function ActThesis() {
  const root = useRef<HTMLElement>(null);
  const pin = useRef<HTMLDivElement>(null);

  useGsapContext(
    () => {
      const mm = gsap.matchMedia();
      mm.add("(min-width: 1024px)", () => {
        gsap.set(
          [".sc-th-statement", ".sc-th-turn", ".sc-th-node", ".sc-th-learns", ".sc-th-foreshadow"],
          { autoAlpha: 0, y: 28 },
        );

        const tl = gsap.timeline({
          defaults: { ease: "power2.out" },
          scrollTrigger: {
            trigger: pin.current,
            start: "top top",
            end: "+=150%",
            pin: pin.current,
            scrub: 0.6,
          },
        });

        tl.to(".sc-th-statement", { autoAlpha: 1, y: 0, duration: 1 })
          .to(".sc-th-turn", { autoAlpha: 1, y: 0, duration: 1 }, ">+0.2")
          .to(".sc-th-node", { autoAlpha: 1, y: 0, duration: 1, stagger: 0.5 }, ">+0.1")
          .to(".sc-th-learns", { autoAlpha: 1, y: 0, duration: 0.8 }, ">-0.1")
          .to(".sc-th-foreshadow", { autoAlpha: 1, y: 0, duration: 0.8 }, ">+0.2");
      });
      return () => mm.revert();
    },
    { scope: root },
  );

  return (
    <section ref={root} id="thesis">
      <div ref={pin} className="flex min-h-dvh items-center">
        <div
          className="mx-auto flex w-full flex-col gap-12 px-6 md:px-12"
          style={{ maxWidth: "var(--sc-container-max)" }}
        >
          <div className="flex max-w-3xl flex-col gap-5">
            <h2
              className="sc-th-statement sc-serif"
              style={{ fontSize: "clamp(1.9rem, 4vw, 3rem)", fontWeight: 600, color: "var(--sc-text)", lineHeight: 1.15 }}
            >
              {THESIS_STATEMENT}
            </h2>
            <p
              className="sc-th-turn sc-serif"
              style={{ fontSize: "clamp(1.4rem, 3vw, 2.1rem)", color: "var(--sc-accent)", lineHeight: 1.2 }}
            >
              {THESIS_TURN}
            </p>
          </div>

          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 sm:gap-12">
            <ThesisNode label={THESIS_STATIC_LABEL} inert caption={THESIS_STATIC_CAPTION} />
            <ThesisNode label={THESIS_HEURISTICS_LABEL} caption={THESIS_HEURISTICS_CAPTION}>
              <div className="sc-th-learns mt-3 flex flex-col gap-1.5">
                <span
                  className="block h-px w-24"
                  style={{ background: "var(--sc-accent)", boxShadow: "0 0 10px var(--sc-accent-glow)" }}
                />
                <span className="sc-serif" style={{ color: "var(--sc-accent)", fontSize: "1.1rem" }}>
                  learns
                </span>
              </div>
            </ThesisNode>
          </div>

          <div className="sc-th-foreshadow">
            <MonoLabel style={{ textTransform: "none", letterSpacing: "0.04em", color: "var(--sc-text-3)" }}>
              {THESIS_FORESHADOW}
            </MonoLabel>
          </div>
        </div>
      </div>
    </section>
  );
}

function ThesisNode({
  label,
  caption,
  inert = false,
  children,
}: {
  label: string;
  caption: string;
  inert?: boolean;
  children?: ReactNode;
}) {
  const color = inert ? "var(--sc-text-3)" : "var(--sc-accent)";
  return (
    <div className="sc-th-node flex items-start gap-4">
      <span
        className={inert ? "" : "sc-breath"}
        style={{
          display: "inline-block",
          width: 14,
          height: 14,
          borderRadius: 999,
          marginTop: 6,
          background: inert ? "transparent" : color,
          border: `1.5px solid ${color}`,
          boxShadow: inert ? "none" : "0 0 14px var(--sc-accent-glow)",
        }}
      />
      <div className="flex flex-col">
        <span className="sc-serif" style={{ fontSize: "1.3rem", color: inert ? "var(--sc-text-2)" : "var(--sc-text)" }}>
          {label}
        </span>
        <span className="sc-mono" style={{ marginTop: 4 }}>
          {caption}
        </span>
        {children}
      </div>
    </div>
  );
}
