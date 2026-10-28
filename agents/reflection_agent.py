import re
import json
import logging
from typing import List, Dict, Any, Optional
import ollama

from config import OLLAMA_HOST, OLLAMA_MODEL, OLLAMA_TIMEOUT, REFLECTION_PROMPT_FILE
from models.schemas import ReflectionResult, ValidationResult, PGSearchCriteria
from services.validation_service import ValidationService

logger = logging.getLogger(__name__)

class ReflectionAgent:
    """
    Performs one-shot reflection and evidence auditing.
    Checks the agent's proposed draft against tool evidence and deterministic validation results.
    Corrects unsupported claims and ensures constraint satisfaction.
    """

    def __init__(self, model_name: Optional[str] = None, host: Optional[str] = None, client: Optional[Any] = None):
        self.model_name = model_name or OLLAMA_MODEL
        self.host = host or OLLAMA_HOST
        self.client = client or ollama.Client(host=self.host, timeout=OLLAMA_TIMEOUT)
        self.system_prompt = self._load_prompt()

    def _load_prompt(self) -> str:
        if REFLECTION_PROMPT_FILE.exists():
            return REFLECTION_PROMPT_FILE.read_text(encoding="utf-8")
        return "You are an Evidence Auditor for SmartStay. Verify facts and correct errors."

    def reflect_and_correct(
        self,
        user_query: str,
        criteria: PGSearchCriteria,
        proposed_draft: str,
        recommended_pg_ids: List[str],
        tool_observations: List[Dict[str, Any]],
        validation_result: ValidationResult,
        distance_data: Optional[Dict[str, float]] = None
    ) -> ReflectionResult:
        """
        Audits draft response. If validation failed or unsupported statements exist,
        generates critique and a corrected response, then re-validates.
        """
        # If deterministic validation already passed with no warnings, draft is solid
        if validation_result.is_valid and not validation_result.warnings:
            return ReflectionResult(
                passed_validation=True,
                needs_correction=False,
                critique="Proposed draft strictly satisfies all budget, amenity, gender, and grounding constraints.",
                correction_suggestions=[],
                corrected_response=proposed_draft
            )

        # Build reflection context
        obs_summary = json.dumps(tool_observations[-5:], indent=2) if tool_observations else "No tool calls recorded."
        val_issues = "\n".join([f"- ERROR: {e}" for e in validation_result.errors] +
                               [f"- WARNING: {w}" for w in validation_result.warnings])

        prompt_message = (
            f"USER QUERY: {user_query}\n\n"
            f"TOOL OBSERVATIONS:\n{obs_summary}\n\n"
            f"PROPOSED DRAFT RESPONSE:\n{proposed_draft}\n\n"
            f"DETERMINISTIC VALIDATION ISSUES:\n{val_issues}\n\n"
            "Please review carefully. If any PG violates budget or amenities or is not grounded, "
            "exclude or correct it. Return Passed (true/false), Critique, and Corrected Response."
        )

        try:
            response = self.client.chat(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt_message}
                ],
                options={"temperature": 0.1, "num_predict": 350}
            )
            raw_output = response["message"]["content"]
            return self._parse_reflection_output(raw_output, proposed_draft, validation_result)
        except Exception as e:
            logger.warning(f"Ollama reflection call failed or timed out: {e}. Using deterministic fallback correction.")
            return self._fallback_correction(user_query, criteria, proposed_draft, validation_result, recommended_pg_ids)

    def _parse_reflection_output(
        self,
        raw_output: str,
        original_draft: str,
        initial_val: ValidationResult
    ) -> ReflectionResult:
        passed = "passed: true" in raw_output.lower()

        critique_match = re.search(r"critique:\s*(.*?)(?=corrected response:|$)", raw_output, re.DOTALL | re.IGNORECASE)
        critique = critique_match.group(1).strip() if critique_match else "Audited draft response."

        corr_match = re.search(r"corrected response:\s*(.*)", raw_output, re.DOTALL | re.IGNORECASE)
        corrected_text = corr_match.group(1).strip() if corr_match else original_draft

        if not passed and not corrected_text:
            corrected_text = original_draft

        return ReflectionResult(
            passed_validation=passed,
            needs_correction=not passed,
            critique=critique,
            correction_suggestions=initial_val.errors,
            corrected_response=corrected_text if not passed else original_draft
        )

    def _fallback_correction(
        self,
        user_query: str,
        criteria: PGSearchCriteria,
        original_draft: str,
        validation_result: ValidationResult,
        recommended_pg_ids: List[str]
    ) -> ReflectionResult:
        """Deterministic fallback correction when LLM reflection is unavailable."""
        from database.data_service import data_service
        from tools.amenity_checker import normalize_amenity

        valid_pgs = []
        for pid in recommended_pg_ids:
            pg = data_service.get_pg_by_id(pid)
            if not pg:
                continue
            if criteria.area and criteria.area.strip().lower() not in ["all areas", "all", ""]:
                if pg.area.strip().lower() != criteria.area.strip().lower():
                    continue
            if criteria.max_rent and pg.monthly_rent > criteria.max_rent:
                continue
            if criteria.gender:
                cg = criteria.gender.strip().lower()
                if "girl" in cg or "female" in cg:
                    if pg.gender not in ["girls", "co-ed"]:
                        continue
                elif "boy" in cg or "male" in cg:
                    if pg.gender not in ["boys", "co-ed"]:
                        continue
                elif "co" in cg and pg.gender != "co-ed":
                    continue
            if criteria.required_amenities:
                pg_norm = [normalize_amenity(a) for a in pg.amenities]
                if any(normalize_amenity(req) not in pg_norm for req in criteria.required_amenities):
                    continue
            valid_pgs.append(pg)

        if valid_pgs:
            lines = [
                f"### Verified PG Recommendations for: '{user_query}'\n",
                "*(Corrected via SmartStay Validation Engine)*\n"
            ]
            for idx, p in enumerate(valid_pgs, 1):
                lines.append(
                    f"{idx}. **{p.name}** ({p.area})\n"
                    f"   - **Monthly Rent**: ₹{p.monthly_rent:,.0f}\n"
                    f"   - **Room Type**: {p.room_type} | **Type**: {p.gender.capitalize()}\n"
                    f"   - **Amenities**: {', '.join(p.amenities)}\n"
                    f"   - **Rating**: {p.rating if p.rating else 'Unrated'}/5.0\n"
                    f"   - **Contact**: {p.contact_number or 'Inquire at desk'}\n"
                )
            corrected_text = "\n".join(lines)
        else:
            corrected_text = (
                f"I reviewed our verified database for your request ('{user_query}'), "
                "but none of the listings could satisfy all your requirements (budget, gender restriction, or mandatory amenities). "
                "Please consider slightly increasing your budget or expanding your target area."
            )

        return ReflectionResult(
            passed_validation=False,
            needs_correction=True,
            critique=f"Deterministic correction applied due to {len(validation_result.errors)} validation errors.",
            correction_suggestions=validation_result.errors,
            corrected_response=corrected_text
        )
