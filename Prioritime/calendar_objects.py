from datetime import datetime


class CalendarItem:
    def __init__(self, name, description, duration, recurring, category, tags, reminders, location):
        self.name = name
        self.description = description
        self.duration = duration
        self.recurring = recurring
        self.category = category
        self.tags = tags
        self.reminders = reminders
        self.location = location
        self.creation_date = datetime


class Event(CalendarItem):
    def __init__(self, start_time, end_time, sub_event, **kwargs):
        super().__init__(**kwargs)
        self.start_time = start_time
        self.end_time = end_time
        self.sub_event = sub_event


class Task(CalendarItem):
    def __init__(self, priority, deadline, **kwargs):
        super().__init__(**kwargs)
        self.priority = priority
        self.deadline = deadline
        self.status = 'active'

    def task_completed(self):
        self.status = 'completed'


class Tasks:
    def __init__(self, list_of_tasks):
        self.list_of_tasks = list_of_tasks

    def add_task(self, task):
        self.list_of_tasks.append(task)


class Schedule:
    def __init__(self, date, day, start_time, end_time, event_list, day_off):
        self.date = date
        self.day = day
        self.start_time = start_time
        self.end_time = end_time
        self.event_list = event_list
        self.free_times = self.check_free_times
        self.day_off = day_off

    def set_day_off(self, day_off=False):
        self.day_off = day_off

    def set_start_time(self, start_time):
        self.start_time = start_time

    def set_end_time(self, end_time):
        self.start_time = end_time

    def check_free_times(self):
        free_times = []
        s_time = self.start_time
        for event in self.event_list:
            if event.start_time > s_time:
                free_times.append(FreeTimeSpace(s_time, event.start_time))
                s_time = event.end_time
        if s_time < self.end_time:
            free_times.append(FreeTimeSpace(s_time, self.start_time))
        return free_times

    def add_event(self, event):
        added = False
        for index, eve in self.event_list:
            if eve.start_time > event.start_time:
                added = True
                self.event_list.insert(index, event)
                break
        if not added:
            self.event_list.append(event)
        self.free_times = self.check_free_times()


class FreeTimeSpace:
    def __init__(self, start_time, end_time):
        self.start_time = start_time
        self.end_time = end_time


class MonthlyCalendar:
    def __init__(self, date, number_of_days, starting_day, list_of_schedules):
        self.date = date
        self.number_of_days = number_of_days
        self.starting_day = starting_day
        self.list_of_schedules = list_of_schedules


class YearlyCalendar:
    def __init__(self, year, list_of_monthly_calendars):
        self.year = year
        self.list_of_monthly_calendars = list_of_monthly_calendars


class Calendar:
    def __init__(self, list_of_yearly_calendars):
        self.list_of_yearly_calendars = list_of_yearly_calendars
