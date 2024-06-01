from rest_framework import serializers


class CalendarItemSerializer(serializers.Serializer):
    _id = serializers.CharField(read_only=True)
    name = serializers.CharField(max_length=200)
    description = serializers.CharField(allow_blank=True, required=False)
    duration = serializers.DurationField(required=False)
    frequency = serializers.CharField(allow_blank=True, required=False)
    category = serializers.CharField(allow_blank=True, required=False)
    tags = serializers.ListField(child=serializers.CharField(), required=False)
    reminders = serializers.IntegerField(default=30)
    location = serializers.CharField(allow_blank=True, required=False)
    creation_date = serializers.DateTimeField()


class EventSerializer(CalendarItemSerializer):
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()
    sub_event = serializers.CharField(allow_blank=True, required=False)
    first_appearance = serializers.DateTimeField(allow_null=True, required=False)


class TaskSerializer(CalendarItemSerializer):
    priority = serializers.CharField(allow_blank=True, required=False)
    deadline = serializers.DateTimeField(allow_null=True, required=False)
    status = serializers.CharField(allow_blank=True, required=False)
    previous_done = serializers.DateTimeField(allow_null=True, required=False)


class ScheduleSerializer(serializers.Serializer):
    date = serializers.DateField()
    day = serializers.CharField(max_length=20)
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()
    event_list = EventSerializer(many=True)
    day_off = serializers.BooleanField(default=False)


class MonthlyCalendarSerializer(serializers.Serializer):
    month = serializers.CharField(max_length=20)
    number_of_days = serializers.IntegerField()
    starting_day = serializers.CharField(max_length=20)
    days = ScheduleSerializer(many=True)


class YearlyCalendarSerializer(serializers.Serializer):
    year = serializers.IntegerField()
    event_count = serializers.IntegerField(default=0)
    days_off = serializers.IntegerField(default=0)
    months = MonthlyCalendarSerializer(many=True)


class CalendarSerializer(serializers.Serializer):
    list_of_yearly_calendars = YearlyCalendarSerializer(many=True)
