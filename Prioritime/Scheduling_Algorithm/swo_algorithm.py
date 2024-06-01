from datetime import datetime, timedelta
from Prioritime.Scheduling_Algorithm.data_preparation import Activity


# consider adding another score for activity that is just part in a preferred time
def utility(activity, planned_start=None, prev_start=None):  # need to think and check the scoring
    score = 0
    current_date = datetime.now()

    if not planned_start:  # for calculating the estimated utility
        planned_start = find_best_start_time(activity, prev_start)

    if not planned_start:
        return float('-inf')

    if activity.deadline and planned_start:
        if planned_start + timedelta(minutes=activity.duration) > activity.deadline:
            return float('-inf')

        # Deadline urgency score based on current date
        days_until_deadline_from_now = abs((activity.deadline - current_date).days)
        urgency_score_now = 1 / (days_until_deadline_from_now + 1)

        # Proximity of planned start to the deadline
        days_until_deadline_from_planned_start = abs((activity.deadline - planned_start).days)
        proximity_score = 1 / (days_until_deadline_from_planned_start + 1)

        # Days between current date and planned start
        days_from_now_to_planned_start = abs((planned_start - current_date).days)
        start_proximity_score = 1 / (days_from_now_to_planned_start + 1)

        # Combine all scores with appropriate weights
        deadline_urgency_score = (urgency_score_now * 0.5) + (proximity_score * 0.3) + (start_proximity_score * 0.2)
        score += deadline_urgency_score * 10  # Adjust this weight as needed

    if activity.preferred_times and planned_start:
        for pref_start, pref_end in activity.preferred_times:
            if (pref_start <= planned_start.time()
                    and (planned_start + timedelta(minutes=activity.duration)).time() <= pref_end):
                score += 10
            elif (pref_start <= (planned_start + timedelta(minutes=activity.duration)).time() <= pref_end
                  or pref_start <= planned_start.time() <= pref_end):
                score += 5

    if activity.preferred_days and planned_start:
        if planned_start.weekday() in activity.preferred_days:
            score += 3

    if prev_start is not None and prev_start == planned_start:
        score -= 15

    return score


def find_best_start_time(activity, prev_start=None):
    best_start_time = None
    best_utility = float('-inf')

    if not activity.free_blocks:
        return best_start_time

    # Check preferred times first
    if activity.preferred_times:
        for pref_start, pref_end in activity.preferred_times:
            for start, end in activity.free_blocks:
                date_pref_start = end.replace(hour=pref_start.hour, minute=pref_start.minute, second=pref_start.second)
                date_pref_end = end.replace(hour=pref_end.hour, minute=pref_end.minute, second=pref_end.second)
                if start <= date_pref_end and date_pref_start + timedelta(minutes=activity.duration) <= end:
                    if date_pref_start >= start:
                        current_utility = utility(activity, date_pref_start, prev_start)
                        if current_utility > best_utility:
                            best_start_time = date_pref_start
                            best_utility = current_utility
                    else:
                        current_utility = utility(activity, start, prev_start)
                        if current_utility > best_utility:
                            best_start_time = start
                            best_utility = current_utility

    # by calculating utility we're already considering if it's a preferred day
    #  if not best_start_time:
    for start, end in activity.free_blocks:
        current_utility = utility(activity, start, prev_start)
        if current_utility > best_utility:
            best_start_time = start
            best_utility = current_utility

    # If no preferred time is found, check all free blocks
    # if not best_st art_time:
    #     if activity.preferred_days:
    #         for start, end in activity.free_blocks:
    #             if start.weekday() in activity.preferred_days:
    #                 current_utility = utility(activity, start)
    #                 if current_utility > best_utility:
    #                     best_start_time = start
    #                     best_utility = current_utility
    #
    # if not best_start_time:
    #     start, end = activity.free_blocks[0]
    #     best_start_time = start

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


def sort_promotions(x):
    a, (b, util) = x
    return util


def same_schedule_results(current_plan, prev_schedule):
    for task_id, task in prev_schedule.items():
        current_start_time, current_end_time = current_plan[task_id]
        if task.start_time != current_start_time or task.end_time != current_end_time:
            return False

    return True


def schedule_activities(activities, max_iterations=1000, early_termination_consecutive=3, prev_schedule=None):
    best_plan = None
    best_utility = float('-inf')
    unscheduled_activities = None
    consecutive_no_improvement = 0

    for act in activities:
        filter_free_time_blocks(act)

    activity_utilities = {
        activity.id: utility(activity, prev_start=prev_schedule[activity.id].start_time if prev_schedule is not None else None) for
        activity in activities}

    # promotion_dict = dict.fromkeys(activity.id for activity in activities)
    promotions = []
    # print('activity utilities: ', activity_utilities)

    base_pq = sorted(activities, key=lambda activity: -activity_utilities[activity.id])

    for _ in range(max_iterations):
        # resting the free time blocks of each activity
        for activity in activities:
            activity.free_blocks = activity.total_free_blocks

        # promoting the activities that was marked for promotion at the last iteration
        # for promotion_id, promote_before_id in promotion_dict.items():
        promotions.sort(key=sort_promotions)
        for promotion_id, (promote_before_id, util) in promotions:
            if promote_before_id:
                index = next((i for i, act in enumerate(base_pq) if act.id == promotion_id), None)
                act_for_promotion = base_pq.pop(index)
                before_index = next((i for i, act in enumerate(base_pq) if act.id == promote_before_id), None)
                base_pq.insert(before_index, act_for_promotion)

        # resting the promotion dictionary for the next iteration
        # promotion_dict = dict.fromkeys(activity.id for activity in activities)
        promotions = []
        pq = base_pq.copy()

        current_plan = dict.fromkeys(act.id for act in activities)
        current_unscheduled_activities = set()

        while pq:
            activity = pq.pop(0)
            best_start_time = find_best_start_time(activity, prev_start=prev_schedule[
                activity.id].start_time if prev_schedule is not None else None)
            if best_start_time:
                planned_end = best_start_time + timedelta(minutes=activity.duration)
                current_plan[activity.id] = (best_start_time, planned_end)
                for other_activity in activities:
                    if current_plan[other_activity.id] is None:
                        update_free_time_blocks(other_activity, best_start_time, planned_end)
                        new_utility = utility(other_activity, prev_start=prev_schedule[
                            activity.id].start_time if prev_schedule is not None else None)
                        if new_utility < activity_utilities[other_activity.id]:
                            if other_activity.id not in dict(promotions).keys():
                                promotions.append((other_activity.id, (activity.id, new_utility)))
                            # if promotion_dict[other_activity.id] is None:
                            #     promotion_dict[other_activity.id] = activity.id
                            #     print(f"{other_activity.id} util = {new_utility} from adding : {activity.id}")
            else:
                current_unscheduled_activities.add(activity.id)

        # Calculate utility including penalties for unscheduled activities
        current_utility = sum(
            utility(act, current_plan[act.id][0] if current_plan[act.id] else None) for act in activities)

        penalty = -len(current_unscheduled_activities) * 20  # Adjust the penalty weight as needed

        # to make sure it would pick a different result
        if prev_schedule is not None:
            if same_schedule_results(current_plan, prev_schedule):
                penalty += float('-inf')

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

    return best_plan, unscheduled_activities


# Example usage
from Prioritime.Model_Logic.calendar_objects import Task
from Prioritime.mongoDB import mongoApi
from datetime import time
from Prioritime.Scheduling_Algorithm.data_preparation import data_preparation, arrange_prev_schedule


user_id = '663cafd680b6dde278303f1d'
general = {'name': 'general', 'start_time': time(hour=8).isoformat(), 'end_time': time(hour=20).isoformat()}
mongoApi.update_preferences(user_id, general)

preference = {
    'name': 'Task_2',
    'possible_days': [0, 1, 2, 3],
    'day_part': {'morning': False, 'noon': True, 'evening': True}
}

mongoApi.update_preferences(user_id, preference)

preference = {
    'name': 'Task_5',
    'possible_days': [0, 1, 3],
    'day_part': {'morning': True, 'noon': False, 'evening': False}
}

mongoApi.update_preferences(user_id, preference)

task_list = [
    Task(_id='123a4223sd', name='Task_1', deadline=datetime(2024, 12, 10).isoformat(), duration=40,
         start_time=datetime(2024, 6, 1, 14, 40).isoformat(), end_time=datetime(2024, 6, 1, 15, 20).isoformat()),

    Task(_id='123as332rd', name='Task_2', deadline=datetime(2024, 8, 10).isoformat(), duration=20,
         start_time=datetime(2024, 6, 3, 16, 0).isoformat(), end_time=datetime(2024, 6, 3, 16, 20).isoformat()),

    Task(_id='123fw3a4sd', name='Task_3', deadline=datetime(2024, 7, 10).isoformat(), duration=400,
         start_time=datetime(2024, 6, 1, 8, 0).isoformat(), end_time=datetime(2024, 6, 1, 14, 40).isoformat()),

    Task(_id='123asf423d', name='Task_4', deadline=datetime(2024, 6, 10).isoformat(), duration=30,
         start_time=datetime(2024, 6, 9, 8, 0).isoformat(), end_time=datetime(2024, 6, 9, 8, 30).isoformat()),

    Task(_id='123asf234d', name='Task_5', deadline=datetime(2024, 11, 10).isoformat(), duration=70,
         start_time=datetime(2024, 6, 3, 8, 0).isoformat(), end_time=datetime(2024, 6, 3, 9, 10).isoformat()),

    Task(_id='123a3424sd', name='Task_6', deadline=datetime(2024, 12, 10).isoformat(), duration=90,
         start_time=datetime(2024, 6, 1, 15, 20).isoformat(), end_time=datetime(2024, 6, 1, 16, 50).isoformat())
]
activities = data_preparation(user_id, task_list, datetime(year=2024, month=6, day=1),
                              datetime(year=2024, month=6, day=30))

prev_schedule = arrange_prev_schedule(task_list)

activities = data_preparation(user_id, task_list, datetime(year=2024, month=6, day=1),
                              datetime(year=2024, month=6, day=30))

# activities = [
#     Activity('1', 60, [(datetime(2024, 5, 25, 8), datetime(2024, 5, 25, 20))], deadline=datetime(2024, 5, 25, 19),
#              preferred_days=[0, 1, 2, 3, 4], preferred_times=[(datetime(2024, 5, 25, 13), datetime(2024, 5, 25, 17))]),
#     Activity('2', 30, [(datetime(2024, 5, 25, 8), datetime(2024, 5, 25, 20))], preferred_days=[0, 1, 2, 3, 4],
#              preferred_times=[(datetime(2024, 5, 25, 14), datetime(2024, 5, 25, 15))]),
#     Activity('3', 30, [(datetime(2024, 5, 25, 8), datetime(2024, 5, 25, 20))], preferred_days=[0, 1, 2, 3, 4],
#              preferred_times=[(datetime(2024, 5, 25, 14), datetime(2024, 5, 25, 15))]),
#     Activity('4', 30, [(datetime(2024, 5, 25, 8), datetime(2024, 5, 25, 14, 30))], preferred_days=[0, 1, 2, 3, 4],
#              preferred_times=[(datetime(2024, 5, 25, 14), datetime(2024, 5, 25, 15))]),
#     Activity('5', 30, [(datetime(2024, 5, 25, 8), datetime(2024, 5, 25, 14, 30))], preferred_days=[0, 1, 2, 3, 4],
#              preferred_times=[(datetime(2024, 5, 25, 14), datetime(2024, 5, 25, 15))]),
#     Activity('6', 30, [(datetime(2024, 5, 25, 14), datetime(2024, 5, 25, 14, 30))], preferred_days=[0, 1, 2, 3, 4]),
#     Activity('7', 60, [(datetime(2024, 5, 25, 8), datetime(2024, 5, 25, 20))], deadline=datetime(2024, 5, 25, 12),
#              preferred_days=[0, 1, 2, 3, 4], preferred_times=[(datetime(2024, 5, 25, 13), datetime(2024, 5, 25, 17))]),
# ]

final_plan, unschedule_tasks = schedule_activities(activities, prev_schedule=prev_schedule)
print(f"plan: {final_plan} , unscheduled activities: {unschedule_tasks}")

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
