import type { AppealRequest, AppealFixture } from "@/lib/types";

export type FlowStep = "intake" | "questions" | "working" | "mirror" | "draft" | "decide";

export interface FlowState {
  step: FlowStep;
  req?: AppealRequest;
  result?: AppealFixture;
  /** Free-form notes added on the mirror step after Q&A. */
  additionalDetails?: string;
  error?: string;
}

export const initialFlow: FlowState = { step: "intake" };

const ORDER: FlowStep[] = ["intake", "questions", "working", "mirror", "draft", "decide"];

export type FlowAction =
  | { type: "BEGIN_QUESTIONS"; req: AppealRequest }
  | { type: "SUBMIT"; req: AppealRequest }
  | { type: "RESULT"; result: AppealFixture }
  | { type: "ERROR"; error: string }
  | { type: "EDIT_LETTER"; letter: string }
  | { type: "ADD_DETAILS"; text: string }
  | { type: "RESTORE"; state: FlowState }
  | { type: "ADVANCE" }
  | { type: "RESET" };

export function flowReducer(state: FlowState, action: FlowAction): FlowState {
  switch (action.type) {
    case "BEGIN_QUESTIONS":
      return { step: "questions", req: action.req };
    case "SUBMIT":
      return { step: "working", req: action.req };
    case "RESULT":
      return { ...state, step: "mirror", result: action.result, error: undefined };
    case "ERROR":
      return { ...state, step: "intake", error: action.error };
    case "EDIT_LETTER":
      return state.result
        ? { ...state, result: { ...state.result, appeal_letter: action.letter } }
        : state;
    case "ADD_DETAILS":
      return { ...state, additionalDetails: action.text || undefined };
    case "RESTORE":
      return { ...action.state, error: undefined };
    case "ADVANCE": {
      const i = ORDER.indexOf(state.step);
      return { ...state, step: ORDER[Math.min(i + 1, ORDER.length - 1)] };
    }
    case "RESET":
      return initialFlow;
    default:
      return state;
  }
}
