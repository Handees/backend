from core import celery


@celery.task(bind=True, name='second_task.stask')
def stask():
    print("working")
