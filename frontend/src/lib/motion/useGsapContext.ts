"use client";

import { useGSAP } from "@gsap/react";
import { useReducedMotion } from "framer-motion";
import type { DependencyList, RefObject } from "react";
import type gsap from "gsap";

type Scope = RefObject<Element | null> | Element | string | null;

type ContextFunc = (
  context: gsap.Context,
  contextSafe?: <T extends (...args: never[]) => unknown>(func: T) => T,
) => void | (() => void);

type UseGsapContextOptions = {
  scope?: Scope;
  dependencies?: DependencyList;
  revertOnUpdate?: boolean;
};

/**
 * Registers a GSAP context scoped to a ref/element with automatic cleanup.
 * Skips animation setup when prefers-reduced-motion is active.
 */
export function useGsapContext(
  setup: ContextFunc,
  { scope, dependencies = [], revertOnUpdate = true }: UseGsapContextOptions = {},
) {
  const reducedMotion = useReducedMotion();

  useGSAP(
    (context, contextSafe) => {
      if (reducedMotion) return;
      return setup(context, contextSafe);
    },
    {
      scope: scope ?? undefined,
      dependencies: [...dependencies, reducedMotion],
      revertOnUpdate,
    },
  );
}

export function prefersReducedMotion(): boolean {
  if (typeof window === "undefined") return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}
