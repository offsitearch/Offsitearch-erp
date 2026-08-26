"""Runtime defaults for leave policy.

Merged over by DB rows from the settings module (group "leave") at runtime —
DB rows override these values key-by-key.
"""

LEAVE_SETTINGS = {
    "policy": {
        "casual": 12,
        "sick": 8,
        "earned": 15,
        "compensatory": 0,
        "maternity": 90,
        "paternity": 15,
        "work_from_home": 48,
        "unpaid": 0,
        "carry_forward": 5,
    }
}
