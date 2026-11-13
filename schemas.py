from pydantic import BaseModel, Field
from typing import List, Literal

class RiskClause(BaseModel):
    clause_title: str = Field(description="Short title of the risky or non-compliant clause")
    page_number: int = Field(description="Exact page number where this clause appears")
    risk_level: Literal["High", "Medium", "Low"] = Field(description="Severity level of the risk")
    exact_quote: str = Field(description="Direct short quote from the contract text")
    explanation: str = Field(description="Clear explanation of why this poses a financial or legal risk")
    recommended_action: str = Field(description="Suggested negotiation edit or mitigation step")
    alternative_wording: str = Field(description="Ready-to-use alternative safe clause text in professional legal phrasing to propose to the other party") # ميزة جديدة: صياغة بديلة جاهزة

class ContractAuditReport(BaseModel):
    contract_summary: str = Field(description="Executive 3-sentence summary of the document")
    overall_risk_score: int = Field(ge=1, le=100, description="Overall risk score from 1 (safe) to 100 (critical)")
    detected_risks: List[RiskClause] = Field(description="List of all detected risks, penalties, and compliance gaps")
    missing_protections: List[str] = Field(description="Standard protective clauses missing from this contract")
    
