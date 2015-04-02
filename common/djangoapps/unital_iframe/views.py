import requests, json, base64

from django.conf import settings
from django.http import HttpRequest, HttpResponse


def iframe_url(request, encoded_url):
    page_url = base64.b64decode(encoded_url)
    response_data = {'iframe_url': fetch_iframe_url(page_url)}
    return HttpResponse(json.dumps(response_data), content_type="application/json")

def fetch_iframe_url(page_url):
    try:
        cookies = dict(JSESSIONID=get_unital_session_key())
        page_url = page_url.replace('#&', 'Do?')
        response = requests.get(page_url, cookies=cookies)
        return json.loads(response.text)['items'][5]['items'][0]['body']['body']['action']['url']
    except:
        return ''

def get_unital_session_key():
    params = {'user': settings.UNITAL_LOGIN, 'password': settings.UNITAL_PASS, 'doaction': 'loginformaction', 'viewType': 'html'}
    response = requests.post(settings.UNITAL_BASE_URL, data=params)
    return response.cookies.get('JSESSIONID')
