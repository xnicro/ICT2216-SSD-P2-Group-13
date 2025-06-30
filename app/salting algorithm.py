from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

# Simulated user database
user_db = {}

# Create an Argon2 hasher instance (customizable parameters)
ph = PasswordHasher(
    time_cost=3,       # number of iterations (default: 2)
    memory_cost=65536, # memory usage in kibibytes (64 MB)
    parallelism=4,     # number of threads
    hash_len=32,       # length of the hash
    salt_len=16        # length of random salt
)

def create_account(username, password):
    if username in user_db:
        print("Username already exists.")
        return
    hashed = ph.hash(password)
    user_db[username] = hashed
    print(f"Account created for {username}")

def verify_login(username, password_attempt):
    hashed = user_db.get(username)
    if not hashed:
        print("User not found.")
        return False
    try:
        ph.verify(hashed, password_attempt)
        print("Login successful.")
        return True
    except VerifyMismatchError:
        print("Incorrect password.")
        return False

# Example usage
if __name__ == "__main__":
    create_account("alice", "password123")
    create_account("Bob", "password123")
    create_account("Bob", "password123")
    print(user_db)
    verify_login("alice", "password123")  # ✅
    verify_login("alice", "wrongpassword")  # ❌