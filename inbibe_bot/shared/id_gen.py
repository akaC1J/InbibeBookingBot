import random
import string
from datetime import datetime


def gen_id() -> str:
    prefix = random.choice(string.ascii_lowercase)
    now = datetime.now().strftime("%y%m%d")
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=5))
    return f"{prefix}{now}-{suffix}"
