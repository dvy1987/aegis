import json
import logging
import os
import random
import uuid
from datetime import UTC, datetime
from pathlib import Path

from app.case_generator import pipeline
from app.case_generator.config import REPO_ROOT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    drafts_dir = REPO_ROOT / "eval" / "cases" / "drafts"
    files = list(drafts_dir.glob("*.json"))
    
    for file_path in files:
        with open(file_path, "r") as f:
            case = json.load(f)
            
        # Check if it's already full
        if "synthetic_provenance" in case and isinstance(case["synthetic_provenance"], dict):
            if "critic_verdicts" in case["synthetic_provenance"]:
                logger.info(f"Skipping {file_path.name}, already rewritten.")
                continue

        logger.info(f"Rewriting {file_path.name}...")
        
        # Add missing patient profile fields
        if "plan_funding_type" not in case["patient_profile"]:
            case["patient_profile"]["plan_funding_type"] = random.choice(["fully_insured", "self_funded"])
            
        case["denial_pattern_sources"] = ["Legacy manual generation"]
        case["submission_timestamp"] = "2026-09-01T10:00:00Z"
        case["denial_timestamp"] = "2026-09-15T14:00:00Z"
        
        # Run final panel to generate critics and appeal difficulty
        logger.info(f"Running final panel for {file_path.name}")
        try:
            final_critics = pipeline._final_panel(
                patient_profile=case["patient_profile"],
                diagnosis=case["patient_profile"]["diagnosis"],
                treatment_requested=case["patient_profile"]["treatment_requested"],
                insurer=case["insurer"],
                denial_type=case["denial_type"],
                denial_letter_text=case["denial_letter_text"],
                clinical_context=case["clinical_context"],
            )
        except Exception as e:
            logger.error(f"Failed to run final panel for {file_path.name}: {e}")
            continue
            
        provenance = {
            "generator_model": "legacy-manual",
            "run_id": f"gen-legacy-{uuid.uuid4().hex[:5]}",
            "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "matrix_cell": {
                "insurer": case["insurer"],
                "denial_type": case["denial_type"],
                "patient_age_band": "unknown",
                "patient_gender": case["patient_profile"]["gender"],
                "specialty": "unknown",
                "sub_tactic": "unknown"
            },
            "prompt_versions": {},
            "banned_topic_filter_version": "1.0.0",
            "schema_version": "1.0.0",
            "diversity_matrix_version": "1.0.0",
            "critic_verdicts": final_critics,
            "human_summary": "Legacy case retroactively augmented with AlphaEval critics.",
            "appeal_difficulty": {
                "score": final_critics.get("appeal_difficulty", {}).get("score", 3) if isinstance(final_critics.get("appeal_difficulty", {}).get("score"), int) else 3,
                "reasoning": final_critics.get("appeal_difficulty", {}).get("reasoning", ""),
                "exploitable_weaknesses": final_critics.get("appeal_difficulty", {}).get("exploitable_weaknesses", []),
                "strong_defenses": final_critics.get("appeal_difficulty", {}).get("strong_defenses", []),
            },
        }
        
        case["synthetic_provenance"] = provenance
        
        # Write back
        with open(file_path, "w") as f:
            json.dump(case, f, indent=2)
            
    logger.info("Done rewriting cases.")

if __name__ == "__main__":
    main()
