from . import mongoApi
from . import calendar_objects
from .Model_Logic import dict_to_entities
import calendar
from datetime import datetime


def get_dally_schedule(user_id, date):
    schedule_dict = mongoApi.get_schedule(user_id, date)
    if schedule_dict:
        schedule = dict_to_entities.dict_to_schedule(schedule_dict)
    else:
        day = int(date['day'])
        month = int(date['month'])
        year = int(date['year'])
        schedule = calendar_objects.Schedule(
            date=int(date['day']),
            day=(calendar.weekday(year, month, day) + 1),
        )
    recurring_events = mongoApi.get_recurring_events(user_id)
    if recurring_events:
        for recurring_event_dict in recurring_events:
            recurring_event = dict_to_entities.dict_to_event(recurring_event_dict)
            if is_recurring_on_date(recurring_event, date):
                schedule.add_event(recurring_event)

    return schedule


def is_recurring_on_date(recurring_event, target_date):
    recurrence_pattern = recurring_event.recurring
    if recurrence_pattern == 'Every Day':
        return True
    else:
        first_appearance = datetime.strptime(recurring_event.first_appearance, "%Y-%m-%d")
        target_date = datetime.strptime(target_date, "%Y-%m-%d")
        if recurrence_pattern == 'Every Month':
            if first_appearance.day == target_date.day:
                return True

        else:
            delta_days = (target_date - first_appearance).days
            if recurrence_pattern == 'Every Week':
                return delta_days % 7 == 0

            elif recurrence_pattern == 'Every 2 Weeks':
                return delta_days % 14 == 0

    return False
