from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import register_events, DjangoJobStore
from apscheduler.triggers.cron import CronTrigger

from django.conf import settings




def daily_job():
  # 실행시킬 Job
  # 여기서 정의하지 않고, import 해도 됨
  pass
  

def start():
  def handle(self, *args, **options):
    scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE) # BlockingScheduler를 사용할 수도 있습니다.
    scheduler.add_jobstore(DjangoJobStore(), "default") 

    scheduler.add_job(
      daily_job,
      trigger=CronTrigger(hour=6, minute=0),  # 매일 오전 6시에 실행
      id="daily_job",  # id는 고유해야합니다. 
      max_instances=1,
      replace_existing=True,
    )

    try:
      scheduler.start() # 없으면 동작하지 않습니다.
    except KeyboardInterrupt:
      scheduler.shutdown()