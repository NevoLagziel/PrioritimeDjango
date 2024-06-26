from rest_framework import serializers


class CalendarItemSerializer(serializers.Serializer):
    _id = serializers.CharField(allow_blank=True)
    name = serializers.CharField(max_length=200, required=True)
    description = serializers.CharField(allow_blank=True, required=False)
    duration = serializers.DurationField(allow_blank=True, required=False)
    frequency = serializers.CharField(allow_blank=True, required=False)
    category = serializers.CharField(allow_blank=True, required=False)
    tags = serializers.ListField(child=serializers.CharField(), allow_blank=True, required=False)
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
