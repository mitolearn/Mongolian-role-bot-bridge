import random
import string

def rand_id(prefix="PAY"):
    tail = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"{prefix}-{tail}"