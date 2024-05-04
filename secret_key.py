import secrets

# Generate a new random secret key
new_secret_key = secrets.token_hex(32)
print(new_secret_key)
