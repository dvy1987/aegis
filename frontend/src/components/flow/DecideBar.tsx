"use client";
import type { AppealFixture } from "@/lib/types";
import { Button } from "@/components/Button";
import { Disclaimer } from "@/components/ui/Disclaimer";
import { CopyIcon, DownloadIcon } from "@/icons";

function download(filename: string, text: string, type: string) {
  const blob = new Blob([text], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function DecideBar({
  result,
  onRestart,
}: {
  result: AppealFixture;
  onRestart: () => void;
}) {
  const letter = result.appeal_letter;
  const base = result.trace_metadata.case_id || "appeal";

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h2 className="font-display text-display-md font-semibold tracking-tight">
          Your appeal is saved as a draft.
        </h2>
        <p className="mt-4 max-w-prose font-body text-lg text-text-secondary">
          Take it from here. Copy it, download it, or share it with your doctor. We don&apos;t file
          anything for you, and the draft lives only on this device.
        </p>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row">
        <Button onClick={() => navigator.clipboard?.writeText(letter)}>
          <CopyIcon size={16} />
          Copy the letter
        </Button>
        <Button variant="secondary" onClick={() => download(`${base}.txt`, letter, "text/plain")}>
          <DownloadIcon size={16} />
          Download .txt
        </Button>
        <Button variant="secondary" onClick={() => download(`${base}.md`, letter, "text/markdown")}>
          <DownloadIcon size={16} />
          Download .md
        </Button>
      </div>

      <p className="font-body text-base text-text-secondary">
        {result.mirror.deadline_note} A person should read this before you file.
      </p>

      <Disclaimer />

      <div>
        <Button variant="ghost" onClick={onRestart}>
          Start another draft
        </Button>
      </div>
    </div>
  );
}
