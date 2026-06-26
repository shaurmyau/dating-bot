import os
from celery import Celery
import celery_config

app = Celery('dating_bot')
app.config_from_object('celery_config')
app.conf.beat_schedule = celery_config.beat_schedule

if __name__ == '__main__':
    app.start()