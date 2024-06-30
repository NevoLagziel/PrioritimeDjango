from datetime import datetime, timedelta


# Function for calculating the utility of an activity, for a certain scheduled time or the best time.
def utility(activity, planned_start=None, prev_start=None):
    score = 0
    current_date = datetime.now()
    # For calculating the best possible utility for an activity (according to the free time blocks available)
    if planned_start is None:  # for calculating the estimated utility
        planned_start = find_best_start_time(activity, prev_start)

    # For handling unscheduled activities at the sum of utilities calculation
    if planned_start == 0:
        return score

    # If couldn't find available time slot returns the lowest utility for making sure promotion
    if planned_start is None:
        return float('-inf')

    # Calculation utility based on factors such as deadline and preferences
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


# Function for finding the best time slot for an activity, from the available time slots for it
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

    for start, end in activity.free_blocks:
        current_utility = utility(activity, start, prev_start)
        if current_utility > best_utility:
            best_start_time = start
            best_utility = current_utility
        # new added for handling prev start
        if prev_start is not None:
            if prev_start == start:
                new_start = (start + timedelta(minutes=activity.duration))
                if new_start <= end:
                    current_utility = utility(activity, new_start, prev_start)
                    if current_utility > best_utility:
                        best_start_time = new_start
                        best_utility = current_utility

    # Making sure the start time is rounded
    if best_start_time:
        best_start_time = (best_start_time + timedelta(seconds=59)).replace(second=0, microsecond=0)

    return best_start_time


# Function for filtering free time blocks for an activity
def filter_free_time_blocks(activity):
    filtered_free_time_blocks = []
    for start, end in activity.free_blocks:
        if start + timedelta(minutes=activity.duration) <= end:
            filtered_free_time_blocks.append((start, end))

    activity.free_blocks = filtered_free_time_blocks


# Function for updating activities free time blocks after the range from start_time to end_time caught
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


# Function for correctly sorting the promotion list by the worst utility first
def sort_promotions(x):
    a, (b, util) = x
    return util


# Function for checking if we got the same result, for re-schedule (date, month)
def same_schedule_results(current_plan, prev_schedule):
    for task_id, task in prev_schedule.items():
        if current_plan[task_id] is None:
            return False

        current_start_time, current_end_time = current_plan[task_id]
        if task.start_time != current_start_time or task.end_time != current_end_time:
            return False

    return True


# SWO algorithm for scheduling, returns the scheduled activities and the unscheduled
def schedule_activities(activities, max_iterations=1000, early_termination_consecutive=3, prev_schedule=None):
    best_plan = None
    best_utility = float('-inf')
    unscheduled_activities = None
    consecutive_no_improvement = 0
    best_possible_utility = 0

    for act in activities:
        filter_free_time_blocks(act)

    # Initializing the possible utility for each activity
    activity_utilities = {
        activity.id: utility(activity,
                             prev_start=None if prev_schedule is None else prev_schedule[activity.id].start_time)
        for
        activity in activities}

    # Calculating the best possible utility just to compare to the result utility
    for i, util in activity_utilities.items():
        if util < (-100):
            util = -20
        best_possible_utility += util

    promotions = []
    base_pq = sorted(activities, key=lambda activity: -activity_utilities[activity.id])
    for _ in range(max_iterations):
        # resting the free time blocks of each activity
        for activity in activities:
            activity.free_blocks = activity.total_free_blocks

        # promoting the activities that was marked for promotion at the last iteration
        promotions.sort(key=sort_promotions)
        for promotion_id, (promote_before_id, util) in promotions:
            if promote_before_id:
                index = next((i for i, act in enumerate(base_pq) if act.id == promotion_id), None)
                act_for_promotion = base_pq.pop(index)
                before_index = next((i for i, act in enumerate(base_pq) if act.id == promote_before_id), None)
                base_pq.insert(before_index, act_for_promotion)

        # resting the promotion dictionary for the next iteration
        promotions = []
        pq = base_pq.copy()

        current_plan = dict.fromkeys(act.id for act in activities)
        current_unscheduled_activities = set()

        while pq:
            # Checking the best available time for each of the activities by the priority queue
            activity = pq.pop(0)
            best_start_time = find_best_start_time(activity,
                                                   prev_start=None if prev_schedule is None else prev_schedule[
                                                       activity.id].start_time)
            # Update the free time blocks left for each activity
            # Calculate the possible utility for each activity yet to scheduled, if went down added to promotion
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
            else:
                current_unscheduled_activities.add(activity.id)

        # Calculate utility for iteration result including penalties for unscheduled activities
        current_utility = sum(
            utility(act, planned_start=current_plan[act.id][0] if current_plan[act.id] else 0,
                    prev_start=None if prev_schedule is None else prev_schedule[act.id].start_time) for act in
            activities)
        penalty = -len(current_unscheduled_activities) * 20  # Adjust the penalty weight as needed

        # To make sure it would pick a different result
        if prev_schedule is not None:
            if same_schedule_results(current_plan, prev_schedule):
                penalty += -100

        current_utility += penalty

        # Checking if iteration result is better than the best so far, if so updating the best result
        if current_utility > best_utility:
            best_plan = current_plan.copy()
            best_utility = current_utility
            unscheduled_activities = current_unscheduled_activities.copy()
            consecutive_no_improvement = 0
        else:
            consecutive_no_improvement += 1

        if consecutive_no_improvement >= early_termination_consecutive:
            break

    # Calculating the percentage of the result utility from the best possible utility
    if best_possible_utility > 0:
        print("Percentage:", ((best_utility/best_possible_utility)*100))

    return best_plan, unscheduled_activities
