class Preference:
    def __init__(self, name, possible_days, day_part=None, **details):
        self.name = name
        self.possible_days = possible_days
        self.day_part = day_part if day_part else {'morning': False, 'noon': False, 'evening': False}
        self.fields = details

    def get_fields(self, field_name):
        return self.fields.get(field_name)

    def __dict__(self):
        preference_dict = {
            'name': self.name,
            'possible_days': self.possible_days,
            'day_part': self.day_part,
            'fields': self.fields,
        }
        return preference_dict


class PreferenceManager:
    def _init_(self):
        self.preferences = {}

    def add_preference(self, name, **attributes):
        self.preferences[name] = attributes

    def find_matching_preference(self, name):
        for preference in self.preferences:
            if preference.name.lower() == name.lower():
                return preference
        return None

    def apply_preferences(self, calendar_item):
        preference = self.preferences.get(calendar_item.name)
        if preference:
            overridden = any(getattr(calendar_item, key) is not None for key in preference)
            if not overridden:
                for attr, value in preference.items():
                    setattr(calendar_item, attr, value)