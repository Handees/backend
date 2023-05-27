BOOKING_NOT_FOUND = "booking with id '{}' not found"
CATEGORY_NOT_FOUND = "category with name '{}' not found"
BOOKING_MADE = "booking request fulfilled"
NEW_BOOKING_MADE = "new booking made"
BOOKING_CANCELED = "{} canceled booking - booking no longer available"
ARTISAN_ARRIVES = "artisan has reached client location"
JOB_STARTED = "new job initiated successfully"
JOB_COMPLETED = "job completed"
UPDATED_JOB_TYPE = "job type updated successfully"
INTERNAL_SERVER_ERROR = "Omo:: 😬an error occured from the backend while trying to perform this task"
SCHEMA_ERROR = 'DataValidationError🤡: Client done screwed up check the data you sent abeg'
JOB_STARTED = 'Artisan started job'
INVALID_TOKEN = 'Token is either expired or invalid 🙃'


def dynamic_msg(msg: str, val):
    return msg.format(val)
