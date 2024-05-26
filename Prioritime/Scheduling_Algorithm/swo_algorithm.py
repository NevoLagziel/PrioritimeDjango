from typing import List, Tuple
#
#
# class Activity:
#     def __init__(self, task_id: str, duration, temporal_domain: List[Tuple[int, int]]):
#         self.task_id = task_id
#         self.duration = duration
#         self.temporal_domain = temporal_domain
#         self.schedule = None  # List of tuples (start_time, duration, location)
#         self.utility = 0  # Utility of scheduling this activity
#
#     def __repr__(self):
#         return f"Activity({self.name})"
#
#
# def difficulty_metric(activity: Activity) -> float:
#     # Example of calculating a simple difficulty metric based on duration and temporal domain
#     total_domain_time = sum(end - start for start, end in activity.temporal_domain)
#     return activity.duration_range[1] / total_domain_time
#
#
# def calculate_utility(schedule: List[Activity]) -> float:
#     # Simplified utility calculation
#     return sum(act.duration_range[1] for act in schedule)  # Just a placeholder
#
#
# def greedy_schedule_activities(activities: List[Activity]) -> List[Activity]:
#     scheduled_activities = []
#     for activity in activities:
#         for time_block_start, time_block_end in activity.temporal_domain:
#             if time_block_end - time_block_start >= activity.duration:
#                 for scheduled_activity in scheduled_activities:
#                     scheduled_start_time, scheduled_duration = scheduled_activity.schedule
#                     if scheduled_start_time + scheduled_duration > time_block_start and scheduled_start_time < time_block_start + activity.duration:
#                         if scheduled_start_time + scheduled_duration + activity.duration > time_block_end:
#                             # false
#                 #
#                 activity.schedule = (time_block_start, activity.duration)
#                 scheduled_activities.append(activity)
#                 break
#     return scheduled_activities
#
#
# def analyze_and_reorder(schedule: List[Activity], priority_queue: List[Activity]) -> List[Activity]:
#     # Placeholder for analyze and reorder logic
#     # For simplicity, reorder based on the calculated utility (reverse the queue)
#     return sorted(priority_queue, key=lambda x: x.utility, reverse=True)
#
#
# def squeaky_wheel_optimization(activities: List[Activity], max_iterations: int = 100) -> List[Activity]:
#     priority_queue = sorted(activities, key=difficulty_metric)
#     best_schedule = []
#     best_utility = float('-inf')
#
#     for iteration in range(max_iterations):
#         schedule = greedy_schedule_activities(priority_queue)
#         current_utility = calculate_utility(schedule)
#
#         if current_utility > best_utility:
#             best_utility = current_utility
#             best_schedule = schedule
#
#         priority_queue = analyze_and_reorder(schedule, priority_queue)
#
#         # Exit condition based on utility improvements
#         if iteration > 10 and current_utility == best_utility:
#             break
#
#     return best_schedule
#
#
# # Example usage
# activities = [
#     Activity("A1", (2, 4), [(0, 10)], 0.5, ["L1"], True, 1, 2, 1, 5),
#     Activity("A2", (1, 3), [(5, 15)], 0.7, ["L2"], False, 1, 1, 0, 0),
#     # Add more activities as needed
# ]
#
# best_schedule = squeaky_wheel_optimization(activities)
# for act in best_schedule:
#     print(f"Activity {act.name} scheduled at {act.schedule}")


from heapq import heappush, heappop
from datetime import datetime, timedelta


class Activity:
    def __init__(self, id, duration, free_blocks, deadline=None, preferred_days=None, preferred_times=None):
        self.id = id
        self.duration = duration
        self.free_blocks = free_blocks  # List of tuples (start_time, end_time)
        self.deadline = deadline
        self.preferred_days = preferred_days  # List of weekdays (e.g., [0, 2, 4])
        self.preferred_times = preferred_times  # List of tuples (start_time, end_time)


# consider adding another score for activity that is just part in a preferred time
def utility(activity, planned_start=None):  # need to think and check the scoring
    penalty = 0
    if activity.deadline and planned_start:
        if planned_start + timedelta(minutes=activity.duration) > activity.deadline:
            return float('-inf')
    if activity.preferred_days and planned_start:
        penalty += 1 if planned_start.weekday() not in activity.preferred_days else 0
    if activity.preferred_times and planned_start:
        for pref_start, pref_end in activity.preferred_times:
            if pref_start <= planned_start < pref_end:
                return 10
            # elif pref_start <= planned_start + duration <= pref_end or pref_start <= planned_start <= pref_end:
            #     return 5
    return -penalty


def estimate_initial_utility(activity):
    # Check for fitting in preferred time blocks
    if activity.preferred_times:
        for pref_start, pref_end in activity.preferred_times:
            if any(start <= pref_start < end and pref_end <= end for start, end in activity.free_blocks):
                return 10  # High utility for having available preferred time blocks

    # Check for fitting within the deadline
    if activity.deadline:
        for start, end in activity.free_blocks:
            if start + timedelta(minutes=activity.duration) <= activity.deadline:
                return 5  # Moderate utility for fitting within free blocks before the deadline

    # General case, prefer to schedule on preferred days
    if activity.preferred_days:
        for start, end in activity.free_blocks:
            if start + timedelta(minutes=activity.duration) <= end:
                if start.weekday() in activity.preferred_days:
                    return 3  # Lower utility for fitting on a preferred day

    return -1  # Default utility if no special conditions are met


def find_best_start_time(activity):
    best_start_time = None
    best_utility = float('-inf')

    # Check preferred times first
    if activity.preferred_times:
        for pref_start, pref_end in activity.preferred_times:
            for start, end in activity.free_blocks:
                if start <= pref_end and pref_start + timedelta(minutes=activity.duration) <= end:
                    if pref_start >= start:
                        current_utility = utility(activity, pref_start)
                        if current_utility > best_utility:
                            best_start_time = pref_start
                            best_utility = current_utility
                    else:
                        current_utility = utility(activity, start)
                        if current_utility > best_utility:
                            best_start_time = start
                            best_utility = current_utility

    # If no preferred time is found, check all free blocks
    if not best_start_time:
        for start, end in activity.free_blocks:
            if activity.preferred_days is None or start.weekday() in activity.preferred_days:
                current_utility = utility(activity, start)
                if current_utility > best_utility:
                    best_start_time = start
                    best_utility = current_utility

    if not best_start_time:
        start, end = activity.free_blocks[0]
        best_start_time = start

    return best_start_time


def filter_free_time_blocks(activity):
    filtered_free_time_blocks = []
    for start, end in activity.free_blocks:
        if start + timedelta(minutes=activity.duration) <= end:
            filtered_free_time_blocks.append((start, end))

    activity.free_blocks = filtered_free_time_blocks


def update_free_time_blocks(activity, start_time, end_time):
    new_free_blocks = []
    for block_start, block_end in activity.free_blocks:
        if block_end <= start_time or block_start >= end_time:
            new_free_blocks.append((block_start, block_end))
        else:
            if block_start < start_time:
                if block_start + timedelta(minutes=activity.duration) <= start_time:
                    new_free_blocks.append((block_start, start_time))

            if block_end > end_time:
                if end_time + timedelta(minutes=activity.duration) <= block_end:
                    new_free_blocks.append((end_time, block_end))

    activity.free_blocks = new_free_blocks


def schedule_activities(activities, max_iterations=1000, early_termination_consecutive=3):
    best_plan = None
    best_utility = float('-inf')
    unscheduled_activities = None
    consecutive_no_improvement = 0

    for act in activities:
        filter_free_time_blocks(act)

    activity_utilities = {activity.id: estimate_initial_utility(activity) for activity in activities}
    print('activity_utilities:', activity_utilities)
    promotion_dict = dict.fromkeys(activity.id for activity in activities)

    base_pq = sorted(activities, key=lambda activity: -activity_utilities[activity.id])

    for _ in range(max_iterations):
        pq = base_pq.copy()
        for promotion_id, promote_before_id in promotion_dict.items():
            if promote_before_id:
                index = next((i for i, act in enumerate(pq) if act.id == promotion_id), None)
                act_for_promotion = pq.pop(index)
                before_index = next((i for i, act in enumerate(pq) if act.id == promote_before_id), None)
                pq.insert(before_index, act_for_promotion)

        current_plan = dict.fromkeys(act.id for act in activities)
        current_utility = 0
        current_unscheduled_activities = set()
        while pq:
            activity = pq.pop(0)
            print(activity)
            best_start_time = find_best_start_time(activity)
            print('best_start_time:', best_start_time)
            if best_start_time:
                planned_end = best_start_time + timedelta(minutes=activity.duration)
                current_plan[activity.id] = (best_start_time, planned_end)
                for other_activity in activities:
                    if current_plan[other_activity.id] is None:
                        update_free_time_blocks(other_activity, best_start_time, planned_end)
                        new_utility = estimate_initial_utility(other_activity)
                        if new_utility < activity_utilities[other_activity.id]:
                            promotion_dict[other_activity.id] = activity.id
            else:
                current_unscheduled_activities.add(activity.id)

        # Calculate utility including penalties for unscheduled activities
        current_utility = sum(utility(act, current_plan[act.id][0] if current_plan[act.id] else None) for act in activities)
        penalty = -len(current_unscheduled_activities) * 5  # Adjust the penalty weight as needed
        current_utility += penalty

        if current_utility > best_utility:
            best_plan = current_plan.copy()
            best_utility = current_utility
            unscheduled_activities = current_unscheduled_activities.copy()
            consecutive_no_improvement = 0
        else:
            consecutive_no_improvement += 1

        if consecutive_no_improvement >= early_termination_consecutive:
            break

    return best_plan, best_utility, unscheduled_activities


# def schedule_activities(activities, max_iterations=1000, early_termination_consecutive=3):
#     best_plan = None
#     best_utility = float('-inf')
#     consecutive_no_improvement = 0
#     activity_utilities = {activity.id: estimate_initial_utility(activity) for activity in activities}
#     promotions = set()
#     unscheduled_activities = set(activity.id for activity in activities)
#
#     for _ in range(max_iterations):
#         pq = []
#         for activity in activities:
#             heappush(pq, (-activity_utilities[activity.id], activity))
#
#         current_plan = dict.fromkeys(act.id for act in activities)
#         current_utility = 0
#         local_promotions = set()
#         unscheduled_activities = set()
#
#         while pq:
#             _, activity = heappop(pq)
#             best_start_time = find_best_start_time(activity)
#
#             if best_start_time:
#                 planned_end = best_start_time + timedelta(minutes=activity.duration)
#                 current_plan[activity.id] = (best_start_time, planned_end)
#                 for other_activity in activities:
#                     if other_activity != activity:
#                         new_utility = utility(other_activity, current_plan[other_activity.id][0] if current_plan[
#                             other_activity.id] else None)
#                         if new_utility < activity_utilities[other_activity.id]:
#                             local_promotions.add(other_activity.id)
#                         activity_utilities[other_activity.id] = new_utility
#             else:
#                 unscheduled_activities.add(activity.id)
#
#         promotions.update(local_promotions)
#
#         promoted_activities = [act for act in activities if act.id in promotions]
#         non_promoted_activities = [act for act in activities if act.id not in promotions]
#
#         # Calculate utility including penalties for unscheduled activities
#         current_utility = sum(
#             utility(act, current_plan[act.id][0] if current_plan[act.id] else None) for act in activities)
#         penalty = -len(unscheduled_activities) * 5  # Adjust the penalty weight as needed
#         current_utility += penalty
#
#         if current_utility > best_utility:
#             best_plan = current_plan.copy()
#             best_utility = current_utility
#             consecutive_no_improvement = 0
#         else:
#             consecutive_no_improvement += 1
#
#         if consecutive_no_improvement >= early_termination_consecutive:
#             break
#
#     unscheduled_activities = [activity for activity in activities if activity.id in unscheduled_activities]
#     return best_plan, best_utility, unscheduled_activities

# Example usage
activities = [
    Activity(1, 60, [(datetime(2024, 5, 25, 8), datetime(2024, 5, 25, 20))], deadline=datetime(2024, 5, 25, 19),
             preferred_days=[0, 1, 2, 3, 4], preferred_times=[(datetime(2024, 5, 25, 13), datetime(2024, 5, 25, 17))]),
    Activity(2, 30, [(datetime(2024, 5, 25, 8), datetime(2024, 5, 25, 20))], preferred_days=[0, 1, 2, 3, 4],
             preferred_times=[(datetime(2024, 5, 25, 14), datetime(2024, 5, 25, 15))]),
]

final_plan, final_utility, unschedule_tasks = schedule_activities(activities)
print(final_plan)
print(f"Total utility: {final_utility}")
