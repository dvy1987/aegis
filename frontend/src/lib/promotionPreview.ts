import type { ShowcaseRunSession } from "@/lib/types";

export type PromotionRuleChange = {
  change: "appended" | "edited" | "revoked" | "removed";
  rule_id: string;
  scope: string;
  funding_scope?: string | null;
  text?: string;
  before_text?: string;
  justification?: string | null;
};

export type PromotionPreviewSection =
  | {
      kind: "drafter";
      title: string;
      before_version: string;
      after_version: string;
      before_text: string;
      after_text: string;
    }
  | {
      kind: "slice_playbook";
      title: string;
      slice_key: string;
      before_version: string;
      after_version: string;
      before_playbook?: Record<string, unknown> | null;
      after_playbook?: Record<string, unknown> | null;
    }
  | {
      kind: "us_playbook";
      title: string;
      before_version: string;
      after_version: string;
      rule_changes: PromotionRuleChange[];
      after_playbook?: Record<string, unknown> | null;
    };

export type PromotionPreview = {
  lift: {
    before_composite: number;
    after_composite: number;
    delta: number;
    per_dimension_deltas: Record<string, number>;
    vetoes: string[];
    is_promotable: boolean;
    diff_summary: string;
    candidate_id: string;
  };
  sections: PromotionPreviewSection[];
};

export function getPromotionPreview(session: ShowcaseRunSession | null): PromotionPreview | null {
  if (!session?.promotion_preview || typeof session.promotion_preview !== "object") {
    return null;
  }
  return session.promotion_preview as PromotionPreview;
}

export function formatPlaybookList(playbook: Record<string, unknown> | null | undefined, key: string): string[] {
  const value = playbook?.[key];
  if (!Array.isArray(value)) return [];
  return value.map((item) => String(item));
}
