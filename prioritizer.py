"""
CCIS Risk Prioritizer — weighted scoring and priority band assignment.

score = w_financial * financial_exposure + w_regulatory * regulatory_severity
      + w_deadline * deadline_urgency + w_counterparty * counterparty_importance

Where source data isn't available, uses documented defaults and marks them
as "estimated" vs "extracted" so the UI can visually distinguish.
"""
import json
from backend.config import W_FINANCIAL, W_REGULATORY, W_DEADLINE, W_COUNTERPARTY
from backend.database import SessionLocal, RiskModel


def prioritize_risks(doc_id: str):
    """Score and band all risks for a document."""
    db = SessionLocal()

    try:
        risks = db.query(RiskModel).filter(RiskModel.doc_id == doc_id).all()

        for risk in risks:
            # Normalise inputs to 0–10 scale
            financial = _normalise_financial(risk.financial_exposure, risk.financial_source)
            regulatory = risk.regulatory_severity or 5.0
            deadline = _deadline_urgency_from_severity(risk.severity_score, risk.risk_type)
            counterparty = _normalise_counterparty(risk.counterparty_importance, risk.counterparty_source)

            # Weighted score
            score = (
                W_FINANCIAL * financial +
                W_REGULATORY * regulatory +
                W_DEADLINE * deadline +
                W_COUNTERPARTY * counterparty
            )

            # Clamp to 0–10
            score = max(0.0, min(10.0, score))

            # Determine band
            if score >= 7.5:
                band = "Critical"
            elif score >= 5.5:
                band = "High"
            elif score >= 3.5:
                band = "Medium"
            else:
                band = "Low"

            risk.severity_score = round(score, 2)
            risk.priority_band = band
            risk.deadline_urgency = deadline

        db.commit()
    finally:
        db.close()


def _normalise_financial(exposure: float | None, source: str) -> float:
    """Normalise financial exposure to 0–10 scale."""
    if exposure is None or source == "estimated":
        return 5.0  # documented default for estimated
    # Tiered: <1K=2, <10K=4, <100K=6, <1M=8, ≥1M=10
    if exposure < 1000:
        return 2.0
    elif exposure < 10000:
        return 4.0
    elif exposure < 100000:
        return 6.0
    elif exposure < 1000000:
        return 8.0
    else:
        return 10.0


def _deadline_urgency_from_severity(severity: float, risk_type: str) -> float:
    """Derive deadline urgency from the detection-phase severity for deadline risks."""
    if risk_type == "deadline_breach":
        return severity  # already calculated by detector
    return 3.0  # default for non-deadline risks


def _normalise_counterparty(importance: float | None, source: str) -> float:
    """Normalise counterparty importance."""
    if importance is None or source == "estimated":
        return 5.0  # documented default
    return max(0.0, min(10.0, importance))
