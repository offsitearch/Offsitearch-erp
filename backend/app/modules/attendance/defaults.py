"""Runtime defaults for attendance policy.

Merged over by DB rows from the settings module (group "attendance") at
runtime — see attendance_service.load_attendance_settings for precedence
(DB rows override these values key-by-key).
"""

ATTENDANCE_SETTINGS = {
    "working_hours": {
        "start": "09:00",
        "end": "18:00",
        "break_minutes": 0,
        "min_hours": 8,
    },
    "late_policy": {
        "grace_minutes": 15,
        "late_threshold": "09:15",
        "half_day_threshold": "11:00",
        "three_late_equals_one_leave": True,
    },
    "working_days": {
        "monday_friday": "full",
        "saturday": "half",
        "sunday": "off",
    },
    "checkin_methods": {
        "web": True,
        "manual": True,
        "qr": False,
        "gps": False,
    },
}
