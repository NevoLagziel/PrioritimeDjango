from datetime import datetime
from datetime import time
from bson import ObjectId


class CalendarItem:
    def __init__(self, name, _id=None, frequency=None, description=None, duration=None, category=None, tags=None,
                 reminders=30, location=None, creation_date=datetime.now().isoformat()):
        self._id = _id if _id is not None else str(ObjectId())
        self.name = name
        self.description = description
        self.duration = duration
        self.frequency = frequency
        self.category = category
        self.tags = tags
        self.reminders = reminders
        self.location = location
        self.creation_date = creation_date

    def __dict__(self):
        calendar_item_dict = {
            "_id": self._id,
            "name": self.name,
            "description": self.description,
            "duration": self.duration,
            "frequency": self.frequency,
            "category": self.category,
            "tags": self.tags,
            "reminders": self.reminders,
            "location": self.location,
            "creation_date": self.creation_date,
        }
        return calendar_item_dict

    def id(self):
        return self._id


class Event(CalendarItem):
    def __init__(self, start_time, end_time, sub_event=None, first_appearance=None, **kwargs):
        super().__init__(**kwargs)
        self.first_appearance = first_appearance
        self.start_time = datetime.fromisoformat(start_time)
        self.end_time = datetime.fromisoformat(end_time)
        self.sub_event = sub_event

    def __dict__(self):
        event_dict = super().__dict__()
        event_dict["first_appearance"] = self.first_appearance
        event_dict['start_time'] = self.start_time.isoformat()
        event_dict['end_time'] = self.end_time.isoformat()
        event_dict['sub_event'] = self.sub_event
        return event_dict


class Task(CalendarItem):
    def __init__(self, priority=None, deadline=None, status=None, previous_done=None, **kwargs):
        super().__init__(**kwargs)
        self.priority = priority
        self.deadline = deadline if deadline is None else datetime.fromisoformat(deadline)
        self.status = status
        self.previous_done = previous_done

    def task_completed(self):
        self.status = 'done'

    def __dict__(self):
        task_dict = super().__dict__()
        task_dict['priority'] = self.priority
        task_dict['deadline'] = self.deadline if self.deadline is None else self.deadline.isoformat()
        task_dict['status'] = self.status
        return task_dict


class Tasks:
    def __init__(self, list_of_tasks):
        self.list_of_tasks = list_of_tasks

    def add_task(self, task):
        self.list_of_tasks.append(task)

    def __dict__(self):
        task_list = []
        for task in self.list_of_tasks:
            task_list.append(task.__dict__())

        dict_task_list = {'task_list': task_list}
        return dict_task_list

    def get_list_by_deadline(self, deadline):
        task_list = []
        for task in self.list_of_tasks:
            if task.deadline is not None and task.deadline.date() == deadline:
                task_list.append(task)

        return task_list


class Schedule:
    def __init__(self, date, day, start_time=None, end_time=None, event_list=None, day_off=False):
        self.date = date
        self.day = day
        self.start_time = start_time
        self.end_time = end_time
        self.event_list = event_list
        self.day_off = day_off

    def __dict__(self):
        dict_event_list = []
        if self.event_list:
            for event in self.event_list:
                dict_event_list.append(event.__dict__())

        dict_schedule = {
            'date': self.date,
            'day': self.day,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'event_list': dict_event_list,
            'day_off': self.day_off,
        }
        return dict_schedule

    def set_day_off(self, day_off=False):
        self.day_off = day_off

    def set_start_time(self, start_time):
        self.start_time = start_time

    def set_end_time(self, end_time):
        self.start_time = end_time

    def free_time_init(self, start_time, end_time):
        free_times = []

        if self.start_time is not None:
            s_time = datetime.strptime(self.start_time, "%H:%M:%S")
            start_time = start_time.replace(hour=s_time.hour, minute=s_time.minute, second=s_time.second)

        if self.end_time is not None:
            e_time = datetime.strptime(self.end_time, "%H:%M:%S")
            end_time = end_time.replace(hour=e_time.hour, minute=e_time.minute, second=e_time.second)

        for event in self.event_list:
            if event.start_time.time() > start_time:
                free_times.append((start_time, event.start_time))
                start_time = event.end_time

        if start_time < end_time:
            free_times.append((start_time, end_time))

        return free_times

    def check_time_availability(self, start_time, duration):
        start_time = datetime.fromisoformat(start_time)
        end_time = (start_time + duration).time().isoformat()
        start_time = start_time.time().isoformat()

        if end_time <= start_time:
            return False

        if self.start_time > start_time or end_time > self.end_time:
            return False

        for event in self.event_list:
            if event.end_time > start_time and event.start_time < end_time:
                return False

        return True

    def add_event(self, new_event):
        self.event_list.append(new_event)
        self.event_list.sort(key=lambda x: x.start_time, reverse=True)

    def add_task(self, new_task):
        if self.check_time_availability(new_task.start_time, new_task.duration):
            self.event_list.append(new_task)
            self.event_list.sort(key=lambda x: x.start_time, reverse=True)
            return True

        return False


class MonthlyCalendar:
    def __init__(self, month, number_of_days, starting_day, list_of_schedules):
        self.month = month
        self.number_of_days = number_of_days
        self.starting_day = starting_day
        self.list_of_schedules = list_of_schedules

    def __dict__(self):
        dict_list_of_schedules = []
        for day in self.list_of_schedules:
            dict_list_of_schedules.append(day.__dict__())

        dict_monthly_calendar = {
            'month': self.month,
            'number_of_days': self.number_of_days,
            'starting_day': self.starting_day,
            'days': dict_list_of_schedules,
        }
        return dict_monthly_calendar


class YearlyCalendar:
    def __init__(self, year, list_of_monthly_calendars, event_count=0, days_off=0):
        self.year = year
        self.event_count = event_count
        self.days_off = days_off
        self.list_of_monthly_calendars = list_of_monthly_calendars

    def __dict__(self):
        dict_list_of_monthly_calendars = []
        for month in self.list_of_monthly_calendars:
            dict_list_of_monthly_calendars.append(month.__dict__())

        dict_yearly_calendar = {
            'year': self.year,
            'event_count': self.event_count,
            'days_off': self.days_off,
            'months': dict_list_of_monthly_calendars
        }
        return dict_yearly_calendar


class Calendar:
    def __init__(self, list_of_yearly_calendars=None):
        self.list_of_yearly_calendars = list_of_yearly_calendars
