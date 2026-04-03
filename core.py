import math
from models import Observation, DebtDetail, Action

class SaaSState:
    def __init__(self, init_cash: float = 50000.0, init_devs: int = 1, init_debt: float = 0.1, init_revenue: float = 0.0):
        self.cash = init_cash
        self.devs = init_devs
        self.tech_debt = init_debt
        self.features_completed = 0
        self.monthly_revenue = init_revenue
        self.current_month = 0
        
    def step(self, action: Action):
        # Apply incoming action
        marketing_push_value = 0.0
        
        if action.action_type == "hire_dev":
            self.devs += action.count
            self.cash -= 2000 * action.count # Initial recruitment fee
        elif action.action_type == "pay_debt":
            reduction = action.amount / 20000.0 # e.g. 20,000 budget fixes 100% of tech debt
            self.tech_debt -= reduction
            self.cash -= action.amount
        elif action.action_type == "marketing_push":
            marketing_push_value = action.amount
            self.cash -= action.amount

        # Member 2 Focus: Diminishing Returns for Dev Productivity
        # The 10th dev is much less productive than the 1st
        effective_devs = math.log1p(self.devs) # natural log of (1+devs)
        
        # Devs build features, tech debt restricts capacity
        new_features = max(0, effective_devs * 2.0 * (1.0 - self.tech_debt))
        self.features_completed += int(new_features)
        
        # Tech debt penalty automatically inflates over time based on new additions
        self.tech_debt += 0.05 + (int(new_features) * 0.01)
        self.tech_debt = max(0.0, min(1.0, self.tech_debt))
        
        # EXACT Formulas specified in prompt requirements:
        new_revenue = (marketing_push_value * 2) - (self.tech_debt * 1000)
        self.monthly_revenue += new_revenue
        if self.monthly_revenue < 0:
            self.monthly_revenue = 0

        # Exact formula for burn rate
        burn_rate = (self.devs * 5000) + 1000
        
        self.cash += self.monthly_revenue - burn_rate
        self.current_month += 1
        
        done = False
        reward = 0.0
        
        # Exact condition requested in prompt
        if self.cash <= 0:
            done = True
            reward = -1.0
            self.cash = 0
            
        return self.get_observation(), done, reward

    def get_observation(self) -> Observation:
        debt_reasoning = f"Current Tech Debt stands at {self.tech_debt*100:.0f}%. "
        impact = ""
        rec = ""
        if self.tech_debt < 0.3:
            debt_reasoning += "The system architecture is relatively maintainable."
            impact = "Feature velocity is high. Minimal degradation of marketing conversions."
            rec = "Continue normal operations, occasional pay_debt is acceptable."
        elif self.tech_debt < 0.7:
            debt_reasoning += "Technical shortcuts are causing bottlenecks and bugs."
            impact = "Marketing conversions are reduced. Noticeable (-1000*tech_debt) MRR penalty."
            rec = "Prioritize pay_debt action to prevent collapse before aggressive marketing."
        else:
            debt_reasoning += "Critical mass of spaghetti code. Stability is fully compromised."
            impact = "Massive ongoing penalty on monthly revenue (-1000 per month scaling). Developer productivity approaching zero."
            rec = "URGENT: Halt all marketing pushes and execute maximum pay_debt budget."
            
        return Observation(
            cash=self.cash,
            devs=self.devs,
            features_completed=self.features_completed,
            monthly_revenue=self.monthly_revenue,
            tech_debt=self.tech_debt,
            tech_debt_details=DebtDetail(
                score=self.tech_debt,
                reasoning=debt_reasoning,
                impact_on_revenue=impact,
                recommendation=rec
            ),
            current_month=self.current_month,
            is_bankrupt=(self.cash <= 0)
        )
