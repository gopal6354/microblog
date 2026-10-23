import random


def generate_otp():
    otp = "".join(str(random.randint(0, 9)) for _ in range(6))
    print(otp)
    return otp
