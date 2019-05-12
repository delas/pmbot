from decouple import config
import requests

GOOGLE_TRACKER = config('GOOGLE_TRACKER')


def track(session_id, command):
    if GOOGLE_TRACKER != "":
        requests.get("https://www.google-analytics.com/collect?v=1&tid={0}&cid={1}&t=event&ec=command&ea={2}".format(GOOGLE_TRACKER, session_id, command))
