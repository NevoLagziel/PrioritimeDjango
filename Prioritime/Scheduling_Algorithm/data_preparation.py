from enum import Enum

from datetime import datetime, time, timedelta
from Prioritime.Model_Logic import user_preferences, calendar_objects
from Prioritime.mongoDB import mongoApi, mongo_utils


class Activity:
    def __init__(self, id, duration, free_blocks=None, deadline=None, preferred_days=None, preferred_times=None):
        self.id = id
        self.duration = duration
        self.free_blocks = free_blocks  # List of tuples (start_time, end_time)
        self.total_free_blocks = free_blocks
        self.deadline = deadline
        self.preferred_days = preferred_days  # List of weekdays (e.g., [0, 2, 4])
        self.preferred_times = preferred_times  # List of tuples (start_time, end_time)

    def __repr__(self):
        return (f"\n"
                f"ID: {self.id}\n"
                f"Duration: {self.duration}\n"
                f"Free time blocks: {self.free_blocks}\n"
                f"Deadline: {self.deadline}\n"
                f"Preferred days: {self.preferred_days}\n"
                f"Preferred times: {self.preferred_times}\n")

    def __str__(self):
        return (f"\n"
                f"ID: {self.id}\n"
                f"Duration: {self.duration}\n"
                f"Free time blocks: {self.free_blocks}\n"
                f"Deadline: {self.deadline}\n"
                f"Preferred days: {self.preferred_days}\n"
                f"Preferred times: {self.preferred_times}\n")


class DayPart(Enum):
    morning = (time(hour=8), time(hour=12))
    afternoon = (time(hour=12), time(hour=16))
    evening = (time(hour=16), time(hour=20))
    night = (time(hour=20), time(hour=23, minute=59))


class Day(Enum):
    Monday = 0
    Tuesday = 1
    Wednesday = 2
    Thursday = 3
    Friday = 4
    Saturday = 5
    Sunday = 6


def create_activities(user_id, task_list, all_free_time_blocks, session):
    activities = []
    user_preferences_dict = mongoApi.get_user_preferences(user_id, session=session)
    preference_manager = user_preferences.PreferenceManager(**user_preferences_dict)
    for task in task_list:
        if task.duration:
            preferred_days = None
            preferred_times = None
            preference = preference_manager.find_matching_preference(task.name)
            if preference:
                preferred_days = preference.days
                preferred_times = arrange_preferred_times(preference.daytime)

            activity = Activity(
                id=task.id(),
                duration=task.duration,
                deadline=task.deadline,
                preferred_days=preferred_days,
                preferred_times=preferred_times,
                free_blocks=arrange_free_time_blocks(task, all_free_time_blocks)
            )
            activities.append(activity)

    return activities


def data_preparation_3(user_id, task_list, begin_date, end_date, session):
    all_free_time_blocks = []
    current_date = begin_date
    preferences = mongoApi.find_preferences(user_id, ['start_time', 'end_time'], session=session)
    start_time = preferences['start_time']
    end_time = preferences['end_time']
    while current_date <= end_date:
        schedule = mongo_utils.get_schedule(user_id, current_date, session=session)
        if schedule is None:
            return None

        if not schedule.day_off:
            all_free_time_blocks.append(schedule.free_time_init(
                datetime.strptime(start_time, "%H:%M:%S")
                .replace(year=current_date.year, month=current_date.month, day=current_date.day),
                datetime.strptime(end_time, "%H:%M:%S")
                .replace(year=current_date.year, month=current_date.month, day=current_date.day)))

        current_date = current_date + timedelta(days=1)

    activities = create_activities(user_id, task_list, all_free_time_blocks, session=session)
    # activities = []
    # for task in task_list:
    #     if task.duration:
    #         preference_dict = mongoApi.find_preference(user_id, task.name, session=session)
    #         preferred_days = None
    #         preferred_times = None
    #         if preference_dict:
    #             preference_dict = preference_dict[task.name]
    #             preference = user_preferences.Preference(**preference_dict)
    #             preferred_days = preference.possible_days
    #             preferred_times = arrange_preferred_times(preference.day_part)
    #
    #         activity = Activity(
    #             id=task.id(),
    #             duration=task.duration,
    #             deadline=task.deadline,
    #             preferred_days=preferred_days,
    #             preferred_times=preferred_times,
    #             free_blocks=arrange_free_time_blocks(task, all_free_time_blocks)
    #         )
    #         activities.append(activity)

    return activities


# The version where the schedules are transferred and updated only at the end
def data_preparation(user_id, task_list, begin_date, end_date, session, schedules=None):
    all_free_time_blocks = []
    current_date = begin_date
    preferences = mongoApi.find_preferences(user_id, ['start_time', 'end_time', 'days_off'], session=session)
    start_time = preferences['start_time']
    end_time = preferences['end_time']
    days_off = preferences['days_off']
    i = 0
    while current_date <= end_date:
        if schedules is None:
            schedule = mongo_utils.get_schedule(user_id, current_date, session=session)
        else:
            schedule = schedules[i]

        if schedule is None:
            return None

        if not schedule.day_off and Day(schedule.day).value not in days_off:
            all_free_time_blocks.append(schedule.free_time_init(
                datetime.strptime(start_time, "%H:%M:%S")
                .replace(year=current_date.year, month=current_date.month, day=current_date.day),
                datetime.strptime(end_time, "%H:%M:%S")
                .replace(year=current_date.year, month=current_date.month, day=current_date.day)))

        current_date = current_date + timedelta(days=1)
        i = i + 1

    activities = create_activities(user_id, task_list, all_free_time_blocks, session=session)
    return activities


def arrange_preferred_times(daytime):
    times = []
    if daytime == 'morning':
        start_time, end_time = DayPart.morning.value
        times.append((start_time, end_time))

    if daytime == 'afternoon':
        start_time, end_time = DayPart.afternoon.value
        times.append((start_time, end_time))

    if daytime == 'evening':
        start_time, end_time = DayPart.evening.value
        times.append((start_time, end_time))

    if daytime == 'night':
        start_time, end_time = DayPart.night.value
        times.append((start_time, end_time))

    return times


def arrange_free_time_blocks(task, all_free_time_blocks):
    task_free_time_blocks = []
    for daly_blocks in all_free_time_blocks:
        for block in daly_blocks:
            start_time, end_time = block
            if start_time + timedelta(minutes=task.duration) <= end_time:
                if task.deadline is None or task.deadline >= end_time:
                    task_free_time_blocks.append((start_time, end_time))

                elif start_time + timedelta(minutes=task.duration) <= task.deadline < end_time:
                    task_free_time_blocks.append((start_time, task.deadline))

    return task_free_time_blocks


def arrange_prev_schedule(task_list):
    prev_schedule = {task.id(): task for task in task_list}
    return prev_schedule
