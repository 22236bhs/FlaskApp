from werkzeug.security import generate_password_hash, check_password_hash

e = generate_password_hash("test")
print(e)

print(check_password_hash(e, "test"))