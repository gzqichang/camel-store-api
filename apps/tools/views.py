import requests
from django.conf import settings
from django.utils import timezone
from rest_framework.serializers import DateTimeField

def add_rig_cron_job():
    """
    添加 自动任务到rig，参考readme
    :return:
    """

    def generate_job(uri_, interval_, next_run_=None):
        job = {
            "uri": f"{project_domain}{uri_}",
            "interval": f"{interval_}",
        }
        if next_run_:
            job.update({"next_run": DateTimeField().to_representation(next_run_)})
        return job

    def generate_next_run(hour, minute):
        tomorrow = timezone.localtime() + timezone.timedelta(days=1)
        next_run = timezone.datetime(tomorrow.year, tomorrow.month, tomorrow.day, hour, minute)
        return next_run

    url = getattr(settings, "RIG_URI_API", None)
    verified_code = getattr(settings, "RIG_URI_VERIFIED_CODE", None)
    domain = getattr(settings, "SHOP_SITE", "")
    project_domain = f"https://{domain}/"

    jobs = [
        generate_job("api/trade/cancel_order/", interval_=1),
        generate_job("api/trade/confirm_receipt/", interval_=60),
        generate_job("api/goods/validatesell/", interval_=1440, next_run_=generate_next_run(0, 5)),
        generate_job("api/pt/settlement/", interval_=1),
        generate_job("api/shop/daily_remind/", interval_=1440, next_run_=generate_next_run(9, 0)),
        generate_job("api/count/calc", interval_=1440, next_run_=generate_next_run(0, 15)),
    ]

    if url is None:
        return

    data = {
        "verified_code": verified_code,
        "data": jobs
    }
    try:
        resp = requests.post(url, json=data)
    except (Exception,):
        print("add rig job error")
    else:
        print("add rig job success")
        return resp
