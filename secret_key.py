import secrets
from datetime import datetime, timedelta

# Generate a new random secret key
new_secret_key = secrets.token_hex(32)
print(new_secret_key)

current_date = "2024-12"
date = datetime.strptime(current_date, "%Y-%m")
print(date)


