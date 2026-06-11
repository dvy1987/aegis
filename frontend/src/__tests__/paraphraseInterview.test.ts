import { describe, expect, it } from "vitest";
import { paraphraseInterview } from "@/lib/flow/paraphraseInterview";
import type { QuestionInterview } from "@/lib/types";

const case168Interview: QuestionInterview = {
  qa_transcript: [
    {
      turn: 1,
      question:
        "Did your oncologist submit a letter or statement to Aetna explaining why you need venetoclax and obinutuzumab instead of their preferred alternatives?",
      answer:
        "I'm not sure. My oncologist prescribed venetoclax and obinutuzumab for my CLL, but I don't know if they sent Aetna a separate letter explaining why those drugs are needed instead of the preferred options.",
    },
    {
      turn: 2,
      question:
        "Have you tried any other medications for your leukemia in the past, or is this your very first time starting treatment for it?",
      answer:
        "I haven't been treated for my leukemia before — this is my first time starting treatment. My oncologist wants to start me on venetoclax and obinutuzumab now because my symptoms and blood counts are bad enough that I need to begin.",
    },
    {
      turn: 3,
      question:
        "Can you describe what specific symptoms you are experiencing and how they are affecting your daily life?",
      answer:
        "I'm tired all the time and get worn out doing normal things like errands or climbing stairs. I have swollen lymph nodes — you can feel lumps in my neck and under my arms — and I've been having night sweats and just feeling run-down for weeks. It's hard to keep up with work and daily life the way I used to.",
    },
  ],
  planned_questions: [],
  patient_gap_note: "",
  skipped: false,
};

describe("paraphraseInterview", () => {
  it("paraphrases strengths without pasting raw answers or leading with uncertainty", () => {
    const { helps, gaps } = paraphraseInterview(case168Interview);
    expect(helps.join(" ")).toMatch(/first treatment/i);
    expect(helps.join(" ")).toMatch(/fatigue|lymph nodes|night sweats/i);
    expect(helps.join(" ")).not.toMatch(/I'm not sure/i);
    expect(gaps.join(" ")).toMatch(/oncologist.*letter/i);
  });

  it("keeps substance when uncertainty is followed by real information", () => {
    const { helps } = paraphraseInterview({
      qa_transcript: [
        {
          turn: 1,
          question: "Did your doctor send a letter?",
          answer: "I'm not sure of the exact date, but my doctor told me they faxed supporting records last month.",
        },
      ],
      planned_questions: [],
      patient_gap_note: "",
      skipped: false,
    });
    expect(helps.length).toBeGreaterThan(0);
    expect(helps.join(" ")).not.toMatch(/^I'm not sure/i);
  });
});
