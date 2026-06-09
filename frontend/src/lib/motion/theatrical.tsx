"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { BEAT_MS } from "./easings";

/** Tier-3 cinematic moments — only one may run at a time (design doc §3.3). */
export type TheatricalMomentId =
  | "hero"
  | "run-ignite"
  | "money-shot"
  | "memory-decay"
  | "finale";

type Waiter = { id: TheatricalMomentId; resolve: () => void };

type TheatricalContextValue = {
  active: TheatricalMomentId | null;
  acquire: (id: TheatricalMomentId) => Promise<void>;
  release: (id: TheatricalMomentId) => void;
  runMoment: (id: TheatricalMomentId, play: () => void, durationMs?: number) => void;
};

const TheatricalContext = createContext<TheatricalContextValue | null>(null);

export function TheatricalProvider({ children }: { children: ReactNode }) {
  const activeRef = useRef<TheatricalMomentId | null>(null);
  const waiters = useRef<Waiter[]>([]);
  const [active, setActive] = useState<TheatricalMomentId | null>(null);

  const sync = useCallback(() => {
    setActive(activeRef.current);
  }, []);

  const acquire = useCallback(async (id: TheatricalMomentId) => {
    if (activeRef.current === null) {
      activeRef.current = id;
      sync();
      return;
    }
    if (activeRef.current === id) return;
    await new Promise<void>((resolve) => {
      waiters.current.push({ id, resolve });
    });
  }, [sync]);

  const release = useCallback(
    (id: TheatricalMomentId) => {
      if (activeRef.current !== id) return;
      const next = waiters.current.shift();
      if (next) {
        activeRef.current = next.id;
        next.resolve();
      } else {
        activeRef.current = null;
      }
      sync();
    },
    [sync],
  );

  const runMoment = useCallback(
    (id: TheatricalMomentId, play: () => void, durationMs = BEAT_MS) => {
      void acquire(id).then(() => {
        play();
        window.setTimeout(() => release(id), durationMs);
      });
    },
    [acquire, release],
  );

  const value = useMemo(
    () => ({ active, acquire, release, runMoment }),
    [active, acquire, release, runMoment],
  );

  return <TheatricalContext.Provider value={value}>{children}</TheatricalContext.Provider>;
}

export function useTheatrical() {
  const ctx = useContext(TheatricalContext);
  if (!ctx) {
    throw new Error("useTheatrical must be used within TheatricalProvider");
  }
  return ctx;
}
