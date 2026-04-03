from pydantic import BaseModel, Field
from typing import Dict, Any

class Action(BaseModel):
    action_type: str = Field(..., description="Type of action: 'hire_dev', 'pay_debt', 'marketing_push'")
    amount: float = Field(default=0.0, description="Amount to spend on pay_debt or marketing_push")
    count: int = Field(default=1, description="Number of items, e.g., developers to hire")

class DebtDetail(BaseModel):
    score: float = Field(..., description="Quantitative tech debt from 0.0 to 1.0")
    reasoning: str = Field(..., description="Explanation of why the debt is at this level and what it implies")
    impact_on_revenue: str = Field(..., description="How exactly this level of debt is affecting the bottom line")
    recommendation: str = Field(..., description="Suggested approach to handle currently observed debt")

class Observation(BaseModel):
    cash: float
    devs: int
    features_completed: int
    monthly_revenue: float
    tech_debt: float
    tech_debt_details: DebtDetail
    current_month: int
    is_bankrupt: bool

class Reward(BaseModel):
    value: float
    reason: str
