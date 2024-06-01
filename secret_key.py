import secrets
from datetime import datetime, timedelta

# Generate a new random secret key
new_secret_key = secrets.token_hex(32)
print(new_secret_key)

current_date = datetime(year=datetime.now().year, month=datetime.now().month, day=datetime.now().day)
deadline = current_date + timedelta(days=1)
print(current_date)
print(deadline)
