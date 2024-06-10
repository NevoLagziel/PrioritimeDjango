import secrets
from datetime import datetime, timedelta
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





