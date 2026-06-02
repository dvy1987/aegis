import type { DataSource } from "./source";
import { demoSource } from "./demo";
import { liveSource } from "./live";

/**
 * Consumer flow (`/appeal`): always the real backend. You are the customer;
 * every draft is a live run.
 */
export const consumerSource: DataSource = liveSource;

/**
 * Judge / behind-the-scenes flow (`/showcase`): recorded v1/v3 evidence from
 * eval runs — not generated live during the demo.
 */
export const showcaseSource: DataSource = {
  listCases: demoSource.listCases,
  getShowcase: demoSource.getShowcase,
  draftAppeal: liveSource.draftAppeal,
};

/** @deprecated Use consumerSource or showcaseSource. */
export function getDataSource(): DataSource {
  return consumerSource;
}
