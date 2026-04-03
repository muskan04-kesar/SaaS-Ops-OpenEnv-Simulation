class TaskDefinition:
    def evaluate(self, state, env_done):
        pass

class EasyTask(TaskDefinition):
    def __init__(self):
        self.level = "easy"
        
    def evaluate(self, state, env_done):
        # 'Easy': Fix 50% tech debt with 20k budget. Initial is 0.8. Target <= 0.4
        if state.tech_debt <= 0.4:
            return 1.0, True, "Task Success: Fixed 50% tech debt!"
        if env_done and state.tech_debt > 0.4:
            return 0.0, True, "Task Failed: Bankrupted before fixing tech debt."
        return 0.0, False, "Task in progress..."

class MediumTask(TaskDefinition):
    def __init__(self):
        self.level = "medium"
        
    def evaluate(self, state, env_done):
        # 'Medium': Reach 10k revenue starting from zero.
        if state.monthly_revenue >= 10000:
            return 1.0, True, "Task Success: Reached Rs. 10,000 monthly revenue target!"
        if env_done:
            return 0.0, True, "Task Failed: Bankrupt."
        return 0.0, False, "Task in progress..."

class HardTask(TaskDefinition):
    def __init__(self):
        self.level = "hard"
        
    def evaluate(self, state, env_done):
        # 'Hard': Survive 12 months while pivoting (switching features -> proxy: features_completed > 5)
        if state.current_month >= 12 and state.cash > 0:
            if state.features_completed >= 5:
                return 1.0, True, f"Task Success: Survived 12 months with {state.features_completed} completed pivoted features!"
            else:
                return 0.0, True, "Task Failed: Survived, but failed pivoting (insufficient feature development)."
        if env_done:
            return 0.0, True, "Task Failed: Bankrupted before 12 months survival."
        return 0.0, False, f"Task in progress... Month {state.current_month}/12"
