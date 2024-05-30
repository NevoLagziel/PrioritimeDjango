from . import mongoApi
from Prioritime.Model_Logic import dict_to_entities, calendar_objects
import calendar
from datetime import datetime
from datetime import date as date_lib


def get_schedule(user_id, date):
    day = int(date['day'])
    month = int(date['month'])
    year = int(date['year'])
    schedule_dict = mongoApi.get_schedule(user_id, date)
    if schedule_dict:
        schedule = dict_to_entities.dict_to_schedule(schedule_dict)
    else:
        schedule = calendar_objects.Schedule(
            date=int(date['day']),
            day=(calendar.weekday(year, month, day) + 1),
        )
    recurring_events = mongoApi.get_recurring_events(user_id)
    if recurring_events:
        for recurring_event_dict in recurring_events:
            recurring_event = dict_to_entities.dict_to_event(recurring_event_dict)
            if is_recurring_on_date(recurring_event, date):
                recurring_event.start_time = ((datetime.fromisoformat(recurring_event.start_time))
                                              .replace(year=year, month=month, day=day)).isoformat()

                recurring_event.end_time = ((datetime.fromisoformat(recurring_event.end_time))
                                            .replace(year=year, month=month, day=day)).isoformat()

                schedule.add_event(recurring_event)

    return schedule


def is_recurring_on_date(recurring_event, target_date):
    recurrence_pattern = recurring_event.frequency
    if recurrence_pattern == 'Every Day':
        return True
    else:
        first_appearance = datetime.fromisoformat(recurring_event.first_appearance)
        target_date = datetime(int(target_date['year']), int(target_date['month']), int(target_date['day']))
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


def update_event(user_id, old_date, new_date, event_id, updated_data):
    # update_fields = {f"{key}": value for key, value in updated_data.items()}
    # event.update(update_fields)
    if old_date.date() == new_date.date():
        if mongoApi.update_event(user_id, event_id, old_date, updated_data):
            return True
    else:
        updated_event = dict_to_entities.create_new_event(updated_data)
        if mongoApi.delete_event(user_id, old_date, event_id):
            if mongoApi.add_event(user_id, updated_event, new_date):
                return True

    return False


def get_task_list(user_id, deadline=None):
    task_list_dict = mongoApi.get_task_list(user_id)
    if not deadline:
        return task_list_dict

    task_list = dict_to_entities.dict_to_task_list(task_list_dict['task_list'])
    deadline = date_lib.fromisoformat(deadline)
    filtered_task_list = calendar_objects.Tasks(task_list.get_list_by_deadline(deadline))
    return filtered_task_list.__dict__()

