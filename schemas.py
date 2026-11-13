from pydantic import BaseModel, Field
from typing import List, Literal, Optional

class RiskClause(BaseModel):
    clause_title: str = Field(description="Short title of the risky or non-compliant clause")
    page_number: int = Field(description="Exact page number where this clause appears")
    risk_level: Literal["High", "Medium", "Low"] = Field(description="Severity level of the risk")
    exact_quote: str = Field(description="Direct short quote from the contract text")
    explanation: str = Field(description="Clear explanation of why this poses a financial or legal risk")
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
    detected_risks: List[RiskClause] = Field(description="List of all detected risks, penalties, and compliance gaps")
    missing_protections: List[str] = Field(description="Standard protective clauses missing from this document")
    rfp_compliance_matrix: Optional[List[RFPRow]] = Field(default=None, description="Only fill if the document is an RFP: compliance matrix rows")
    
