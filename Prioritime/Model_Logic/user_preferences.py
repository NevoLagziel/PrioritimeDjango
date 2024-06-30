from datetime import time, datetime

default_start_time = time(hour=8)
default_end_time = time(hour=20)


class Preference:
    def __init__(self, name, days=None, daytime=None, **fields):
        self.name = name  # this been deleted : self.name = name.lower()
        self.days = days
        self.daytime = daytime
        self.fields = fields

    def __dict__(self):
        preference_dict = {
            'name': self.name,
            'days': self.days,
            'daytime': self.daytime,
        }
        for key, value in self.fields.items():
            preference_dict[key] = value
        return preference_dict


class PreferenceManager:
    def __init__(self, preferences=None, days_off=None, start_time=None, end_time=None):
        start_time = datetime.strptime(start_time, "%H:%M:%S").time() if start_time is not None else default_start_time
        end_time = datetime.strptime(end_time, "%H:%M:%S").time() if end_time is not None else default_end_time
        if start_time >= end_time:
            start_time = default_start_time
            end_time = default_end_time

        preference_dict = {}
        if preferences is not None:
            if type(preferences) is list:
                for value in preferences:
                    preference_dict[value.get('name')] = Preference(**value)
            else:
                for key, value in preferences.items():
                    preference_dict[key] = Preference(**value)

        self.preferences = preference_dict
        self.days_off = days_off if days_off is not None else []
        self.start_time = start_time
        self.end_time = end_time

    def add_preference(self, name, **attributes):
        self.preferences[name] = Preference(name, **attributes)

    def find_matching_preference(self, name):
        for key, value in self.preferences.items():
            if key.lower() == name.lower():
                return value

        return None

    def __dict__(self):
        user_preferences = {
            'preferences': {name: preference.__dict__() for name, preference in self.preferences.items()},
            'days_off': self.days_off,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat()
        }
        return user_preferences

    # sending to the frontend different dict
    def dict_for_json(self):
        user_preferences = {
            'preferences': [],
            'days_off': self.days_off,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat()
        }
        for name, preference in self.preferences.items():
            user_preferences['preferences'].append(preference.__dict__())
        return user_preferences
