"use client";

import Link from "next/link";
import { useState } from "react";
import { Wordmark } from "@/components/Wordmark";
import { SettingsPanel } from "@/components/SettingsPanel";
import { SettingsIcon } from "@/icons";

export function Nav() {
  const [settingsOpen, setSettingsOpen] = useState(false);

  return (
    <>
      <header className="w-full">
        <div className="mx-auto flex max-w-(--container-wide) items-center justify-between px-6 pt-8 md:px-12 md:pt-12">
          <Link href="/" aria-label="Aegis home">
            <Wordmark />
          </Link>
          <nav
            aria-label="Primary"
            className="flex items-center gap-4 font-body text-sm text-text-secondary md:gap-6"
          >
            <Link href="/appeal" className="transition-colors hover:text-text-primary">
              Draft an appeal
            </Link>
            <Link href="/showcase" className="transition-colors hover:text-text-primary">
              How Aegis learns
            </Link>
            <button
              type="button"
              onClick={() => setSettingsOpen(true)}
              className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 transition-colors hover:bg-surface-tertiary hover:text-text-primary"
              aria-label="Open settings"
            >
              <SettingsIcon size={20} aria-hidden />
              <span className="hidden sm:inline">Settings</span>
            </button>
          </nav>
        </div>
      </header>
      <SettingsPanel open={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </>
  );
}
