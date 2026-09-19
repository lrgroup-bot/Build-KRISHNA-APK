from __future__ import annotations


class VerificationReviewer:
    """Second-pass logical reviewer. Provider independence is reported, never assumed."""

    def review(self, investigation: dict, verification: dict,
               primary_provider: str = "", reviewer_provider: str = "") -> dict:
        independent = bool(primary_provider and reviewer_provider and primary_provider != reviewer_provider)
        evidence_count = len(investigation.get("evidence") or [])
        hypotheses = investigation.get("hypotheses") or []
        verified = bool(verification.get("verified"))
        concerns = []
        if evidence_count == 0:
            concerns.append("no evidence collected")
        if not hypotheses:
            concerns.append("no root-cause hypotheses")
        if not verified:
            concerns.append("verification gate not passed")
        return {
            "accepted": verified and evidence_count > 0 and bool(hypotheses),
            "independent_provider": independent,
            "primary_provider": primary_provider or None,
            "reviewer_provider": reviewer_provider or None,
            "concerns": concerns,
        }
