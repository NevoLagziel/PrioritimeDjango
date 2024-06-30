import random
from datetime import datetime, timedelta, time
from bson import ObjectId
from faker import Faker
from db_connection import db
from Prioritime.mongoDB import mongo_utils
from django.contrib.auth.hashers import make_password
import os
import django
import json

# Set the DJANGO_SETTINGS_MODULE environment variable
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "PrioritimeDjango.settings")

# Configure Django settings
django.setup()

# Initialize Faker
fake = Faker()

users = db['users']


# Function to generate random events
def generate_random_events(num_events):
    events = []
    recurrence_options = ['Once', 'Every Day', 'Every Week', 'Every Month', 'Every 2 Weeks']
    recurrence_weights = [0.92, 0.02, 0.02, 0.02, 0.02]
    for _ in range(num_events):
        # start_datetime = fake.date_time_this_year(after_now=True)
        start_datetime = fake.date_time_between_dates(datetime_start=datetime.now(),
                                                      datetime_end=(datetime.now() + timedelta(days=150)))
        duration = random.randint(30, 500)
        end_datetime = start_datetime + timedelta(minutes=duration)
        if end_datetime != start_datetime.date():
            end_datetime = start_datetime.replace(hour=23, minute=59, second=59)

        recurring = random.choices(recurrence_options, weights=recurrence_weights, k=1)[0]
        events.append({
            "_id": str(ObjectId()),
            "name": fake.sentence(nb_words=3).replace('.', ''),
            "description": fake.text(),
            "start_time": start_datetime.isoformat(),
            "end_time": end_datetime.isoformat(),
            "duration": duration,
            "location": fake.address(),
            "category": random.choice(["Work", "Personal", "Health", "Workout", "Home", "Clean"]),
            "frequency": recurring,
            "tags": [fake.word() for _ in range(random.randint(1, 3))],
            "reminders": random.randint(1, 60),
            "first_appearance": None if recurring == "Once" else start_datetime.isoformat(),
            "sub_event": None,
            "item_type": "event" if recurring == "Once" else "recurring event",
            "creation_date": (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat()
        })
    return events


# Function to generate random tasks
def generate_random_tasks(num_tasks):
    tasks = []
    recurrence_options = ['Once', 'Every Day', 'Every Week', 'Every Month', 'Every 2 Weeks']
    recurrence_weights = [0.92, 0.02, 0.02, 0.02, 0.02]
    for _ in range(num_tasks):
        recurring = random.choices(recurrence_options, weights=recurrence_weights, k=1)[0]
        tasks.append({
            "_id": str(ObjectId()),
            "name": fake.sentence(nb_words=3).replace('.', ''),
            "description": fake.text(),
            "start_time": None,
            "end_time": None,
            "duration": random.randint(10, 120),
            "frequency": recurring,
            "category": random.choice(["Work", "Personal", "Health", "Workout", "Home", "Clean"]),
            "tags": [fake.word() for _ in range(random.randint(1, 3))],
            "reminders": random.randint(1, 60),
            "location": fake.address(),
            "priority": random.choice(["low", "medium", "high"]),
            "deadline": (datetime.now() + timedelta(days=random.randint(1, 30))).isoformat(),
            "status": "pending",
            "previous_done": None,
            "item_type": "task" if recurring == "Once" else "recurring task",
            "creation_date": (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat()
        })
    return tasks


# Function to generate a user with random events and tasks
def generate_random_user(num_events=2, num_tasks=3):
    email = fake.email()
    password = fake.password()
    hashed_password = make_password(password)
    user = {
        "firstName": fake.first_name(),
        "lastName": fake.last_name(),
        "email": email,
        "not_hashed_pass": password,
        "password": hashed_password,
        "confirmation_token": fake.uuid4(),
        'email_confirmed': True,
        "calendar": [],
        'task_list': [],
        'recurring_events': [],
        'recurring_tasks': [],
        'user_preferences': {
            'preferences': {},
            'days_off': [],
            'start_time': time(hour=8).isoformat(),
            'end_time': time(hour=20).isoformat(),
        }
    }

    current_year = datetime.now().year
    year_entry = mongo_utils.create_new_year(current_year).__dict__()

    events = generate_random_events(num_events)
    tasks = generate_random_tasks(num_tasks)

    normal_reduced_events_list = []
    recurring_reduced_events_list = []
    normal_reduced_tasks_list = []
    recurring_reduced_tasks_list = []

    num_of_events = 0
    for event in events:
        if event['item_type'] == 'event':
            date = datetime.fromisoformat(event['start_time'])
            year_entry['months'][date.month - 1]['days'][date.day - 1]['event_list'].append(event)
            num_of_events += 1
            normal_reduced_events_list.append(
                {'_id': event['_id'], 'name': event['name'], "start_time": event['start_time'],
                 "end_time": event['end_time']})
        else:
            user["recurring_events"].append(event)
            recurring_reduced_events_list.append(
                {'_id': event['_id'], 'name': event['name'], "start_time": event['start_time'],
                 "end_time": event['end_time'], "frequency": event['frequency']})

    year_entry['event_count'] = num_of_events
    user["calendar"].append(year_entry)

    for task in tasks:
        if task['item_type'] == 'task':
            user['task_list'].append(task)
            normal_reduced_tasks_list.append({'_id': task['_id'], 'name': task['name'], "duration": task['duration']})
        else:
            user["recurring_tasks"].append(task)
            recurring_reduced_tasks_list.append({'_id': task['_id'], 'name': task['name'], "duration": task['duration'],
                                                 'frequency': task['frequency']})

    user_to_print = {
        user['firstName']: {
            'email': user['email'],
            'password': user['not_hashed_pass'],
            'task_list': normal_reduced_tasks_list,
            'event_list': normal_reduced_events_list,
            'recurring_tasks': recurring_reduced_tasks_list,
            'recurring_events': recurring_reduced_events_list,
        }
    }
    return user, user_to_print


# Generate and insert mockup data
num_users = 1
for _ in range(num_users):
    random_user, printable_user = generate_random_user(50, 50)
    users.insert_one(random_user)
    print(json.dumps(printable_user, indent=4))
