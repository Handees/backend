from .push_booking_to_queue import huey


@huey.task(bind=True, name='second_task.stask')
def stask():
    print("working")
