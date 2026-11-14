from pydantic import BaseModel, Field
from typing import List, Literal, Optional

class RiskClause(BaseModel):
    clause_title: str = Field(description="Short title of the risky or non-compliant clause")
    page_number: int = Field(description="Exact page number where this clause appears")
    risk_level: Literal["High", "Medium", "Low"] = Field(description="Severity level of the risk")
    exact_quote: str = Field(description="Direct short quote from the contract text")
    explanation: str = Field(description="Clear explanation of why this poses a financial or legal risk")
    financial_exposure_estimate: Optional[str] = Field(description="Estimated financial impact or liability cap risk in currency equivalent if applicable")
    playbook_violation: Optional[str] = Field(description="How this violates the company's custom internal playbook rules, if specified")
    recommended_action: str = Field(description="Suggested negotiation edit or mitigation step")
    alternative_wording: str = Field(description="Ready-to-use alternative safe clause text in professional legal phrasing")
class RFPRow(BaseModel):
    requirement_number: str = Field(description="Section or clause number from the RFP")
    client_requirement: str = Field(description="Summary of what the client is asking for")
    compliance_status: Literal["Compliant", "Non-Compliant", "Partially Compliant"] = Field(description="Company's compliance status")
    bidder_response: str = Field(description="Professional proposed response or mitigation strategy for this requirement")
class ContractAuditReport(BaseModel):
    document_type: Literal["Contract", "RFP (Request for Proposal)"] = Field(description="Identified document type")
    contract_summary: str = Field(description="Executive 3-sentence summary of the document")
    overall_risk_score: int = Field(ge=1, le=100, description="Overall risk score from 1 (safe) to 100 (critical)")
    estimated_financial_exposure: Optional[str] = Field(description="Estimated total potential financial exposure or loss if all major risks materialize (e.g., '$50,000 or 20% of contract value')")
    detected_risks: List[RiskClause] = Field(description="List of all detected risks, penalties, and compliance gaps")
    missing_protections: List[str] = Field(description="Standard protective clauses missing from this document")
    rfp_compliance_matrix: Optional[List[RFPRow]] = Field(default=None, description="Only fill if the document is an RFP: compliance matrix rows")
    negotiation_email_draft: Optional[str] = Field(default=None, description="A formal, diplomatic, and professional email draft addressed to the opposing party/client summarizing the required contractual revisions and alternative wordings.")
class VersionChangeItem(BaseModel):
    clause_topic: str = Field(description="Topic or section of the modified clause")
    change_status: Literal["Improved / Accepted", "Partially Addressed", "Ignored / Unchanged", "New Hidden Risk Added"] = Field(description="Evaluation of the change between versions")
    original_text_summary: str = Field(description="Summary of what the original contract stated")
    revised_text_summary: str = Field(description="Summary of what the revised contract now states")
    risk_impact: str = Field(description="Impact of this change on the company's legal/financial safety")

class ContractComparisonReport(BaseModel):
    overall_improvement_score: int = Field(ge=1, le=100, description="Score from 1 (worse/no progress) to 100 (all risks resolved)")
    executive_comparison_summary: str = Field(description="Executive summary of how much safer the revised version is compared to the original")
    changes_breakdown: List[VersionChangeItem] = Field(description="Detailed comparison of key changes and remaining traps")
    final_recommendation: Literal["Safe to Sign", "Requires Further Negotiation", "Do Not Sign - Critical Traps Remain"] = Field(description="Final legal recommendation")
class NegotiationRound(BaseModel):
    round_number: int = Field(description="Sequential round number starting from 1")
    version_label: str = Field(description="Version name or label for this round")
    key_changes_summary: str = Field(description="Summary of the main edits made in this version compared to the previous one")
    resolved_issues: List[str] = Field(description="Risks or negotiation points that were resolved or improved in this version")
    unresolved_or_new_risks: List[str] = Field(description="Remaining unresolved traps or newly introduced risks in this version")
    round_risk_score: int = Field(ge=1, le=100, description="Risk score for this version from 1 (safest) to 100 (highest risk)")

class MultiRoundTimelineReport(BaseModel):
    timeline_summary: str = Field(description="Overall executive summary of how the negotiation progressed across all versions")
    rounds: List[NegotiationRound] = Field(description="Chronological breakdown of each version/round")
    overall_negotiation_verdict: str = Field(description="Current readiness status and final legal stance")
    next_round_leverage_tips: List[str] = Field(description="Actionable negotiation points and leverage tips for the next round")
    
