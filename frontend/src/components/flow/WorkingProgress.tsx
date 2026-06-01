"use client";
import { useEffect, useState } from "react";
import { useReducedMotion } from "framer-motion";
import { ProgressHairline } from "@/components/ui/ProgressHairline";

const LINES = ["Reading your denial…", "Drafting your appeal…", "Almost done."];

export function WorkingProgress() {
  const reduced = useReducedMotion();
  const [i, setI] = useState(0);

  useEffect(() => {
    if (reduced) return;
    const t = setInterval(() => setI((n) => Math.min(n + 1, LINES.length - 1)), 1400);
    return () => clearInterval(t);
  }, [reduced]);

  const line = reduced ? "Working on your appeal…" : LINES[i];
  const ratio = reduced ? 0.5 : (i + 1) / LINES.length;

  return (
    <div className="flex flex-col gap-8 py-16">
      <ProgressHairline ratio={ratio} />
      <p className="font-display text-display-sm font-semibold tracking-tight text-text-primary">
        {line}
      </p>
    </div>
  );
}
