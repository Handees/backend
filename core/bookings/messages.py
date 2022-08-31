BOOKING_NOT_FOUND = "booking with id '{}' not found"
CATEGORY_NOT_FOUND = "category with name '{}' not found"
BOOKING_MADE = "booking request fulfilled"


def dynamic_msg(msg: str, val):
    return msg.format(val)
