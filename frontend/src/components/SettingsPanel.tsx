"use client";

import { useCallback, useEffect, useId, useState } from "react";
import { Button } from "@/components/Button";
import { StatusDot } from "@/components/ui/StatusDot";
import {
  AEGIS_V1_API_URL,
  checkBackendHealth,
  getDiscoveryEnabled,
  setDiscoveryEnabled,
  notifySettingsChanged,
  type BackendStatus,
} from "@/lib/settings";
import { cn } from "@/lib/cn";

function Switch({
  id,
  checked,
  disabled,
  onChange,
  label,
}: {
  id: string;
  checked: boolean;
  disabled?: boolean;
  onChange: (next: boolean) => void;
  label: string;
}) {
  return (
    <button
      id={id}
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={() => !disabled && onChange(!checked)}
      className={cn(
        "relative h-7 w-12 shrink-0 rounded-full border transition-colors",
        "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-sage",
        checked ? "border-accent-sage bg-accent-sage" : "border-border-strong bg-surface-tertiary",
        disabled && "cursor-not-allowed opacity-50",
      )}
    >
      <span
        className={cn(
          "absolute top-0.5 left-0.5 h-5 w-5 rounded-full bg-surface-primary transition-transform",
          checked && "translate-x-5",
        )}
      />
    </button>
  );
}

function statusLabel(status: BackendStatus): string {
  if (status === "checking") return "Checking connection to drafting service…";
  if (status === "connected") return "Connected — appeals run for real";
  if (status === "offline") return "Not connected — aegis-v1-api may be down";
  return "Check that the drafting service is running";
}

export function SettingsPanel({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const discoveryId = useId();

  const [discovery, setDiscovery] = useState(true);
  const [status, setStatus] = useState<BackendStatus>("unknown");

  const refreshStatus = useCallback(async () => {
    setStatus("checking");
    setStatus(await checkBackendHealth());
  }, []);

  useEffect(() => {
    if (!open) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setDiscovery(getDiscoveryEnabled());
    void refreshStatus();
  }, [open, refreshStatus]);

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  const canUseDiscovery = status === "connected";

  function save() {
    setDiscoveryEnabled(canUseDiscovery ? discovery : false);
    notifySettingsChanged();
    onClose();
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-surface-overlay/40 p-4 sm:items-center"
      role="presentation"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="settings-title"
        className="w-full max-w-lg rounded-lg border border-border-default bg-surface-primary p-6 shadow-[var(--elevation-modal)]"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 id="settings-title" className="font-display text-xl font-semibold tracking-tight">
          Settings
        </h2>
        <p className="mt-2 font-body text-sm text-text-secondary leading-relaxed">
          Draft an appeal always uses the live service. How Aegis learns uses recorded
          evidence on its own page.
        </p>

        <div
          className="mt-6 flex items-center gap-3 rounded-md border border-border-default bg-surface-secondary px-4 py-3"
          aria-live="polite"
        >
          <StatusDot tone={status === "connected" ? "sage" : "clay"} />
          <p className="font-body text-sm text-text-primary">{statusLabel(status)}</p>
        </div>

        <div className="mt-8 flex flex-col gap-8">
          <div className="flex flex-col gap-2">
            <p className="font-body text-sm font-medium text-text-primary">Drafting service</p>
            <p className="font-mono text-xs text-text-secondary break-all">{AEGIS_V1_API_URL}</p>
            <Button type="button" variant="secondary" className="self-start" onClick={() => void refreshStatus()}>
              Check connection
            </Button>
          </div>

          <div className="flex items-start justify-between gap-4 border-t border-border-default pt-8">
            <div className="flex-1">
              <label htmlFor={discoveryId} className="font-body text-base font-medium text-text-primary">
                Trusted source lookup
              </label>
              <p className="mt-2 font-body text-sm text-text-secondary leading-relaxed">
                If the library is thin, Aegis may add up to five vetted public sources before
                drafting. On by default when connected.
              </p>
              {status !== "connected" && (
                <p className="mt-3 font-body text-sm text-text-tertiary">
                  Connect to the drafting service first.
                </p>
              )}
            </div>
            <Switch
              id={discoveryId}
              label="Trusted source lookup"
              checked={discovery}
              disabled={!canUseDiscovery}
              onChange={setDiscovery}
            />
          </div>
        </div>

        <div className="mt-8 flex justify-end gap-3">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="button" variant="primary" onClick={save}>
            Save
          </Button>
        </div>
      </div>
    </div>
  );
}
