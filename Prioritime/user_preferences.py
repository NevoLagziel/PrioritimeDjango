import datetime
from calendar_objects import CalendarItem


class Preference:
    class Preference:
        def _init_(self, name, **details):
            self.name = name
            self.fields = details

        def get_fields(self, field_name):
            return self.fields.get(field_name)


class PreferenceManager:
    def _init_(self):
        self.preferences = {}

    def add_preference(self, name, **attributes):
        self.preferences[name] = attributes

    # TODO use the function below in apply
    def find_matching_preference(self, name):
        for preference in self.preferences:
            if preference.name.lower() == name.lower():
                return preference
        return None

    def apply_preferences(self, calendar_item):

        # apply happens only when the user adds item to the calander
        # TODO understand where should that function be located

        preference = self.preferences.get(calendar_item.name)
        if preference:
            overridden = any(getattr(calendar_item, key) is not None for key in preference)
            if not overridden:
                for attr, value in preference.items():
                    setattr(calendar_item, attr, value)

    # def create_calendar_item(self, name, recurring, **kwargs):
    #     """Create a CalendarItem dynamically with possible preference application."""
    #     item_attrs = {'name': name, 'recurring': recurring}
    #
    #     # If the item's name matches a preference and no additional attributes are specified,
    #     # apply the preference attributes. Otherwise, use the provided attributes.
    #     if name in self.preferences and not any(kwargs.values()):
    #         item_attrs.update(self.preferences[name])
    #     item_attrs.update(kwargs)
    #
    #     return CalendarItem(**item_attrs)

    # def create_calendar_item(self, name, recurring, description=None, duration=None, category=None, tags=None,
    #                          reminders=30, location=None, **kwargs):
    #     matching_preference = self.preferences_manager.find_matching_preference(name)
    #     if matching_preference and 'duration' not in kwargs:
    #         duration = matching_preference.fields.get('duration', duration)
    #         category = matching_preference.fields.get('category', category)
    #         tags = matching_preference.fields.get('tags', tags)
    #
    #     if 'duration' in kwargs:
    #         duration = kwargs['duration']
    #     if 'category' in kwargs:
    #         category = kwargs['category']
    #     if 'tags' in kwargs:
    #         tags = kwargs['tags']
    #
    #     return CalendarItem(name, recurring, description, duration, category, tags, reminders, location, **kwargs)

    # TODO user should implement this class
