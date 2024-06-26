import secrets
import calendar
from datetime import datetime, timedelta, time
from enum import Enum
from Prioritime.Model_Logic import calendar_objects


from faker import Faker

fake = Faker()

# Generate a new random secret key
new_secret_key = secrets.token_hex(32)
print(new_secret_key)

current_date = "2024-12"
date = datetime.strptime(current_date, "%Y-%m")
print(date)

year = fake.date_time_this_year(after_now=True)
print('year', year)

import pprint

my_list = [1, 2, 3, 4, 5]
print("Using pprint:")
pprint.pprint(my_list)

import json
import pprint

my_dict = {
    'name': 'Alice',
    'age': 30,
    'address': {
        'street': '123 Maple Street',
        'city': 'Wonderland',
        'zip': '12345'
    },
    'hobbies': ['reading', 'gardening', 'painting']
}

print("Using pprint:")
pprint.pprint(my_dict)

print("\nUsing json.dumps:")
print(json.dumps(my_dict, indent=4))

from pprint import pformat

my_dict = {'name': 'Alice', 'age': 30, 'city': 'Wonderland'}
print(pformat(my_dict))

print(datetime.today().replace(hour=0, minute=0, second=0, microsecond=0))

arr = ['somthing', 'somthing', 'somthing', 'yes']

print(type(arr) is list)
print(list)


class Day(Enum):
    Sunday = 0
    Monday = 1
    Tuesday = 2
    Wednesday = 3
    Thursday = 4
    Friday = 5
    Saturday = 6


print(Day(3).name)


temp = {'name': 'dani', 'age': 24, 'city': 'tel'}
updated = {'name': 'shalom', 'age': None, 'city': ''}
temp.update({key: val} for key, val in updated.items() if val is not None)
print(temp)


print((calendar.monthrange(2024, 9)[0] + 1) % 7)

task = calendar_objects.Task(name="name", reminders=None)

print(task.__dict__())
