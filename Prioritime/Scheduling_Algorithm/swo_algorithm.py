from typing import List, Tuple


class Activity:
    def __init__(self, task_id: str, duration, temporal_domain: List[Tuple[int, int]]):
        self.task_id = task_id
        self.duration = duration
        self.temporal_domain = temporal_domain
        self.schedule = None  # List of tuples (start_time, duration, location)
        self.utility = 0  # Utility of scheduling this activity

    def __repr__(self):
        return f"Activity({self.name})"


def difficulty_metric(activity: Activity) -> float:
    # Example of calculating a simple difficulty metric based on duration and temporal domain
    total_domain_time = sum(end - start for start, end in activity.temporal_domain)
    return activity.duration_range[1] / total_domain_time


def calculate_utility(schedule: List[Activity]) -> float:
    # Simplified utility calculation
    return sum(act.duration_range[1] for act in schedule)  # Just a placeholder


def greedy_schedule_activities(activities: List[Activity]) -> List[Activity]:
    scheduled_activities = []
    for activity in activities:
        for time_block_start, time_block_end in activity.temporal_domain:
            if time_block_end - time_block_start >= activity.duration:
                for scheduled_activity in scheduled_activities:
                    scheduled_start_time, scheduled_duration = scheduled_activity.schedule
                    if scheduled_start_time + scheduled_duration > time_block_start and scheduled_start_time < time_block_start + activity.duration:
                        if scheduled_start_time + scheduled_duration + activity.duration > time_block_end:
                            # false
                #
                activity.schedule = (time_block_start, activity.duration)
                scheduled_activities.append(activity)
                break
    return scheduled_activities


def analyze_and_reorder(schedule: List[Activity], priority_queue: List[Activity]) -> List[Activity]:
    # Placeholder for analyze and reorder logic
    # For simplicity, reorder based on the calculated utility (reverse the queue)
    return sorted(priority_queue, key=lambda x: x.utility, reverse=True)


def squeaky_wheel_optimization(activities: List[Activity], max_iterations: int = 100) -> List[Activity]:
    priority_queue = sorted(activities, key=difficulty_metric)
    best_schedule = []
    best_utility = float('-inf')

    for iteration in range(max_iterations):
        schedule = greedy_schedule_activities(priority_queue)
        current_utility = calculate_utility(schedule)

        if current_utility > best_utility:
            best_utility = current_utility
            best_schedule = schedule

        priority_queue = analyze_and_reorder(schedule, priority_queue)

        # Exit condition based on utility improvements
        if iteration > 10 and current_utility == best_utility:
            break

    return best_schedule


# Example usage
activities = [
    Activity("A1", (2, 4), [(0, 10)], 0.5, ["L1"], True, 1, 2, 1, 5),
    Activity("A2", (1, 3), [(5, 15)], 0.7, ["L2"], False, 1, 1, 0, 0),
    # Add more activities as needed
]

best_schedule = squeaky_wheel_optimization(activities)
for act in best_schedule:
    print(f"Activity {act.name} scheduled at {act.schedule}")
