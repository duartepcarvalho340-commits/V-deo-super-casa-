"""Editable timing for the Meta Muse spec film (seconds). Scene boundaries follow audio/voice_timing.json."""
FPS = 60
DURATION = 21.75
SCENES = {
    "intro": (0.0, 1.4),       # the orb ignites, the ribbon writes the name
    "prompt": (1.4, 3.0),      # one request, typed once
    "travel": (3.0, 5.0),      # flight + hotel booked
    "email": (5.0, 7.2),       # email written and sent
    "shop": (7.2, 9.3),        # purchase paid
    "background": (9.3, 11.5), # keeps working with the app closed
    "memory": (11.5, 13.2),    # remembers what you like, suggests
    "platforms": (13.2, 15.8), # phone, Mac, WhatsApp, glasses
    "resolve": (15.8, 19.75),  # message + brand
    "endcard": (19.75, 21.75), # creator card, full two seconds
}
EVENTS = {
    "type_start": 1.6, "type_end": 2.55, "send": 2.75,
    "flight_ok": 3.75, "hotel_ok": 4.3,
    "email_send": 5.85, "email_sent": 6.6,
    "pay_press": 7.9, "paid": 8.25,
    "lock": 9.55, "task_1": 9.95, "task_2": 10.5, "task_3": 11.05,
    "mem_1": 11.6, "mem_2": 11.95, "mem_3": 12.3, "suggest": 12.6,
    "st_app": 13.5, "st_mac": 14.3, "st_whatsapp": 14.95, "st_glasses": 15.45,
    "converge": 15.8, "msg_1": 16.0, "msg_2": 17.25, "brand": 18.25, "to_endcard": 19.45, "endcard": 19.75,
}
NAME = "Duarte Carvalho"
HANDLE = "@duartecarvalho"
AVATAR_INITIALS = "DC"
