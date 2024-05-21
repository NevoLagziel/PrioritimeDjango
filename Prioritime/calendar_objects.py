from datetime import datetime
from datetime import time
from bson import ObjectId

time_format = "%H:%M:%S"


class CalendarItem:
    def __init__(self, name, _id=None, recurring=None, description=None, duration=None, category=None, tags=None,
                 reminders=30, location=None, creation_date=datetime.now().isoformat()):
        self._id = _id if _id is not None else str(ObjectId())
        self.name = name
        self.description = description
        self.duration = duration
        self.recurring = recurring
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
            "duration": str(self.duration),
            "recurring": self.recurring,
            "category": self.category,
            "tags": self.tags,
            "reminders": self.reminders,
            "location": self.location,
            "creation_date": self.creation_date,
        }
        return calendar_item_dict


class Event(CalendarItem):
    def __init__(self, start_time, end_time, sub_event=None, first_appearance=None, **kwargs):
        super().__init__(**kwargs)
        self.first_appearance = first_appearance
        self.start_time = start_time
        self.end_time = end_time
        self.sub_event = sub_event

    def __dict__(self):
        event_dict = super().__dict__()
        event_dict["first_appearance"] = self.first_appearance
        event_dict['start_time'] = self.start_time
        event_dict['end_time'] = self.end_time
        event_dict['sub_event'] = self.sub_event
        return event_dict


class Task(CalendarItem):
    def __init__(self, priority=None, deadline=None, status='active', **kwargs):
        super().__init__(**kwargs)
        self.priority = priority
        self.deadline = deadline
        self.status = status

    def task_completed(self):
        self.status = 'completed'

    def __dict__(self):
        task_dict = super().__dict__()
        task_dict['priority'] = self.priority
        task_dict['deadline'] = self.deadline
        task_dict['status'] = self.status
        return task_dict


class Tasks:
    def __init__(self, list_of_tasks):
        self.list_of_tasks = list_of_tasks

    def add_task(self, task):
        self.list_of_tasks.append(task)


class Schedule:
    def __init__(self, date, day, start_time=time(8, 0).isoformat(), end_time=time(20, 0).isoformat(),
                 event_list=None, day_off=False):
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

    def free_time_init(self):
        free_times = []
        s_time = self.start_time
        for event in self.event_list:
            if event.start_time > s_time:
                free_times.append(FreeTimeSpace(s_time, event.start_time))
                s_time = event.end_time

        if s_time < self.end_time:
            free_times.append(FreeTimeSpace(s_time, self.start_time))

        return free_times

    def check_time_availability(self, start_time, duration):
        start_time = datetime.strptime(start_time, time_format)
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


class FreeTimeSpace:
    def __init__(self, start_time, end_time):
        self.start_time = start_time
        self.end_time = end_time


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
    def __init__(self, year, list_of_monthly_calendars, number_of_events=0):
        self.year = year
        self.number_of_events = number_of_events
        self.list_of_monthly_calendars = list_of_monthly_calendars

    def __dict__(self):
        dict_list_of_monthly_calendars = []
        for month in self.list_of_monthly_calendars:
            dict_list_of_monthly_calendars.append(month.__dict__())

        dict_yearly_calendar = {
            'year': self.year,
            'months': dict_list_of_monthly_calendars
        }
        return dict_yearly_calendar


class Calendar:
    def __init__(self, list_of_yearly_calendars=None):
        self.list_of_yearly_calendars = list_of_yearly_calendars
