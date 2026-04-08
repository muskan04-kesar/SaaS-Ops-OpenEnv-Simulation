class TaskDefinition:
    """Base class for all task graders."""

    def evaluate(self, state, env_done: bool):
        """
        Returns (reward: float, done: bool, message: str).
        reward must be a partial signal at every step, not just at terminal states.
        """
        raise NotImplementedError


class EasyTask(TaskDefinition):
    """
    Goal: Reduce tech debt from 0.8 down to <= 0.4 before going bankrupt.
    Starting cash: Rs.20,000  |  Starting debt: 80%

    Partial reward: how much debt has been cleared toward the 0.4 target.
    Full reward (1.0) when debt reaches 40% or below.
    """

    INITIAL_DEBT = 0.8
    TARGET_DEBT = 0.4

    def __init__(self):
        self.level = "easy"

    def evaluate(self, state, env_done: bool):
        # --- Success ---
        if state.tech_debt <= self.TARGET_DEBT:
            return 0.99, True, "Task Success: Tech debt cleaned up to 40%. Codebase is healthy!"

        # --- Bankruptcy ---
        if env_done:
            # Still give partial credit for how far they got
            progress = max(0.0, (self.INITIAL_DEBT - state.tech_debt) / (self.INITIAL_DEBT - self.TARGET_DEBT))
            reward = max(0.01, round(progress * 0.5, 3))
            return reward, True, (
                f"Task Failed: Bankrupt with debt still at {state.tech_debt * 100:.0f}%. "
                f"Partial progress: {progress * 100:.0f}%."
            )

        # --- Partial progress signal (every step) ---
        # Scales from 0.0 (debt still at 80%) to just under 1.0 (debt near 40%)
        progress = max(0.0, (self.INITIAL_DEBT - state.tech_debt) / (self.INITIAL_DEBT - self.TARGET_DEBT))
        partial_reward = max(0.01, round(progress * 0.8, 3))   # Cap at 0.8 so 0.99 is reserved for true success
        return partial_reward, False, (
            f"In progress: debt at {state.tech_debt * 100:.0f}% "
            f"(target ≤ 40%). Progress: {progress * 100:.0f}%."
        )


class MediumTask(TaskDefinition):
    """
    Goal: Reach Rs.10,000 Monthly Recurring Revenue starting from Rs.0.
    Starting cash: Rs.50,000  |  Starting debt: 10%

    Partial reward: proportional to how close MRR is to the Rs.10,000 target.
    """

    TARGET_REVENUE = 10_000.0

    def __init__(self):
        self.level = "medium"

    def evaluate(self, state, env_done: bool):
        # --- Success ---
        if state.monthly_revenue >= self.TARGET_REVENUE:
            return 0.99, True, (
                f"Task Success: Reached Rs.{state.monthly_revenue:,.0f} MRR. "
                f"Product-market fit achieved!"
            )

        # --- Bankruptcy ---
        if env_done:
            progress = min(1.0, state.monthly_revenue / self.TARGET_REVENUE)
            reward = max(0.01, round(progress * 0.5, 3))
            return reward, True, (
                f"Task Failed: Bankrupt at Rs.{state.monthly_revenue:,.0f} MRR "
                f"({progress * 100:.0f}% of Rs.10,000 target)."
            )

        # --- Partial progress signal (every step) ---
        # score = current_revenue / target_revenue, capped at 1.0
        progress = min(1.0, state.monthly_revenue / self.TARGET_REVENUE)
        partial_reward = max(0.01, round(progress * 0.8, 3))
        return partial_reward, False, (
            f"In progress: Rs.{state.monthly_revenue:,.0f} MRR "
            f"({progress * 100:.0f}% of Rs.10,000 target)."
        )


class HardTask(TaskDefinition):
    """
    Goal: Survive 12 months AND complete at least 12 features (the 'pivot').
    Starting cash: Rs.30,000  |  Devs: 3  |  Starting debt: 40%  |  Seed revenue: Rs.2,000

    Partial reward combines two dimensions:
      - Time survival   (how many of 12 months completed)
      - Feature pivot   (how many of 12 features shipped)
    Both are weighted equally.
    """

    TARGET_MONTHS = 12
    TARGET_FEATURES = 12   # Fixed: was 5 in original, openenv.yaml says 12

    def __init__(self):
        self.level = "hard"

    def evaluate(self, state, env_done: bool):
        month_progress = min(1.0, state.current_month / self.TARGET_MONTHS)
        feature_progress = min(1.0, state.features_completed / self.TARGET_FEATURES)

        # --- Full success: survived 12 months AND shipped 12 features ---
        if state.current_month >= self.TARGET_MONTHS and state.cash > 0:
            if state.features_completed >= self.TARGET_FEATURES:
                return 0.99, True, (
                    f"Task Success: Survived 12 months and shipped "
                    f"{state.features_completed} pivot features. The startup lives!"
                )
            else:
                # Survived but didn't pivot enough
                partial = max(0.01, round((feature_progress * 0.5), 3))
                return partial, True, (
                    f"Task Failed: Survived 12 months but only shipped "
                    f"{state.features_completed}/{self.TARGET_FEATURES} pivot features. "
                    f"Partial score: {partial}."
                )

        # --- Bankruptcy ---
        if env_done:
            partial = max(0.01, round((month_progress + feature_progress) * 0.25, 3))
            return partial, True, (
                f"Task Failed: Bankrupt at month {state.current_month}/12 "
                f"with {state.features_completed}/{self.TARGET_FEATURES} features shipped. "
                f"Partial score: {partial}."
            )

        # --- Partial progress signal (every step) ---
        partial_reward = max(0.01, round((month_progress + feature_progress) * 0.4, 3))
        return partial_reward, False, (
            f"In progress: Month {state.current_month}/{self.TARGET_MONTHS} | "
            f"Features {state.features_completed}/{self.TARGET_FEATURES} | "
            f"Cash Rs.{state.cash:,.0f}"
        )
