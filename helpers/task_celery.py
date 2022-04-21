from celery import Celery


class MCelery:
    def __init__(self, app=None):
        self.app = app
        self.includes = []
        if self.app:
            self.init_app(self.app)

    def init_app(self, app):
        celery = Celery(
            app.import_name,
            backend=app.config['CELERY_BACKEND'],
            broker=app.config['CELERY_BROKER_URL'],
            include=self.includes
        )
        celery.conf.update(app.config)

        class ContextTask(celery.Task):
            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return self.run(*args, **kwargs)

        celery.Task = ContextTask
        return celery
