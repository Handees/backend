from .booking_tasks import huey


@huey.task(bind=True, name='second_task.stask')
def stask():
    print("working")
