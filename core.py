import math
import random
from models import Observation, DebtDetail, Action


class SaaSState:
    def __init__(
        self,
        init_cash: float = 50000.0,
        init_devs: int = 1,
        init_debt: float = 0.1,
        init_revenue: float = 0.0,
    ):
        self.cash = init_cash
        self.devs = init_devs
        self.tech_debt = init_debt
        self.features_completed = 0
        self.monthly_revenue = init_revenue
        self.current_month = 0
        self.last_event = None  # Tracks the stochastic event that fired this month

    # ------------------------------------------------------------------
    # Stochastic Events
    # Each event has a 5% chance of firing per step.
    # Returns a (description_string, modifier_dict) or None.
    # ------------------------------------------------------------------
    def _roll_stochastic_event(self) -> dict | None:
        if random.random() > 0.15:   # 15% chance of ANY event each month
            return None

        events = [
            {
                "name": "key_dev_quit",
                "message": "A key developer quit! Lost 1 dev this month.",
                "dev_delta": -1,
                "cash_delta": 0,
                "revenue_delta": 0,
                "debt_delta": 0.05,   # Codebase suffers without them
            },
            {
                "name": "viral_spike",
                "message": "A viral tweet sent a traffic spike! +Rs.3,000 bonus revenue this month.",
                "dev_delta": 0,
                "cash_delta": 0,
                "revenue_delta": 3000,
                "debt_delta": 0.03,   # Rushed to handle load
            },
            {
                "name": "server_outage",
                "message": "Server provider went down! Emergency costs -Rs.2,000 and lost some revenue.",
                "dev_delta": 0,
                "cash_delta": -2000,
                "revenue_delta": -1500,
                "debt_delta": 0.04,
            },
            {
                "name": "investor_interest",
                "message": "An angel investor showed interest! Bonus cash injection of Rs.5,000.",
                "dev_delta": 0,
                "cash_delta": 5000,
                "revenue_delta": 0,
                "debt_delta": 0,
            },
            {
                "name": "bug_flood",
                "message": "A critical bug flooded support tickets! Devs pulled off features to fix it.",
                "dev_delta": 0,
                "cash_delta": 0,
                "revenue_delta": -2000,
                "debt_delta": 0.08,
            },
        ]
        return random.choice(events)

    # ------------------------------------------------------------------
    # Main simulation step
    # ------------------------------------------------------------------
    def step(self, action: Action):
        marketing_push_value = 0.0
        self.last_event = None

        # --- Apply the chosen action ---
        if action.action_type == "hire_dev":
            self.devs += action.count
            self.cash -= 2000 * action.count   # One-time recruitment fee

        elif action.action_type == "pay_debt":
            # Rs.20,000 fully erases 100% tech debt
            reduction = action.amount / 20000.0
            self.tech_debt = max(0.0, self.tech_debt - reduction)
            self.cash -= action.amount

        elif action.action_type == "marketing_push":
            marketing_push_value = action.amount
            self.cash -= action.amount

        # --- Stochastic event (fires before simulation math) ---
        event = self._roll_stochastic_event()
        if event:
            self.last_event = event
            self.devs = max(1, self.devs + event["dev_delta"])   # Never drop below 1 dev
            self.cash += event["cash_delta"]
            # Revenue delta is applied below after base revenue is computed

        # --- Developer productivity (diminishing returns) ---
        # log1p means the 10th dev adds far less than the 1st
        effective_devs = math.log1p(self.devs)

        # --- Feature building (tech debt throttles velocity) ---
        new_features = max(0.0, effective_devs * 2.0 * (1.0 - self.tech_debt))
        self.features_completed += int(new_features)

        # --- Tech debt accumulation ---
        # Flat entropy (0.02/month) + cost of shipping fast (0.01 per feature)
        # FIXED: was 0.05 flat which made debt unbeatable; lowered to 0.02
        self.tech_debt += 0.02 + (int(new_features) * 0.01)
        self.tech_debt = max(0.0, min(1.0, self.tech_debt))

        # --- Revenue calculation ---
        # FIXED: monthly_revenue is now SET each step, not accumulated.
        # A marketing push raises the MRR ceiling; tech debt erodes it.
        # Without a marketing push this month, existing MRR decays slightly (churn proxy).
        if marketing_push_value > 0:
            # New marketing contribution lifts MRR
            marketing_lift = marketing_push_value * 2.0
            debt_penalty = self.tech_debt * 1000.0
            self.monthly_revenue = max(0.0, self.monthly_revenue + marketing_lift - debt_penalty)
        else:
            # Natural churn: 5% MRR decay each month with no marketing, minus debt penalty
            churn_loss = self.monthly_revenue * 0.05
            debt_penalty = self.tech_debt * 500.0   # Smaller passive penalty
            self.monthly_revenue = max(0.0, self.monthly_revenue - churn_loss - debt_penalty)

        # Apply event revenue delta (can be positive or negative)
        if event:
            self.monthly_revenue = max(0.0, self.monthly_revenue + event["revenue_delta"])

        # --- Burn rate ---
        burn_rate = (self.devs * 5000) + 1000

        # --- Cash flow ---
        self.cash += self.monthly_revenue - burn_rate
        self.current_month += 1

        # --- Bankruptcy check ---
        done = False
        reward = 0.0
        if self.cash <= 0:
            done = True
            reward = -1.0
            self.cash = 0

        return self.get_observation(), done, reward

    # ------------------------------------------------------------------
    # Build structured observation for the agent
    # ------------------------------------------------------------------
    def get_observation(self) -> Observation:
        debt_reasoning = f"Current Tech Debt stands at {self.tech_debt * 100:.0f}%. "
        impact = ""
        rec = ""

        if self.tech_debt < 0.3:
            debt_reasoning += "The system architecture is relatively maintainable."
            impact = "Feature velocity is high. Minimal degradation of marketing conversions."
            rec = "Continue normal operations. Occasional pay_debt is fine."
        elif self.tech_debt < 0.7:
            debt_reasoning += "Technical shortcuts are causing bottlenecks and bugs."
            impact = "Marketing conversions are reduced. Active MRR penalty each month."
            rec = "Prioritize pay_debt before aggressive marketing to avoid revenue collapse."
        else:
            debt_reasoning += "Critical mass of spaghetti code. Stability fully compromised."
            impact = "Massive MRR penalty every month. Developer productivity near zero."
            rec = "URGENT: Stop all marketing pushes. Execute maximum pay_debt immediately."

        event_message = self.last_event["message"] if self.last_event else None

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
                recommendation=rec,
            ),
            current_month=self.current_month,
            is_bankrupt=(self.cash <= 0),
            event_message=event_message,
        )
