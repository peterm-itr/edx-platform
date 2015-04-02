import requests, json, base64

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from unital_iframe import UNITAL_LOGIN, UNITAL_PASS, UNITAL_BASE_URL


def iframe_url(request, url):
    url = base64.b64decode(url)
    response_data = {'iframe_url': fetch_iframe_url(url)}
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
    params = {'user': UNITAL_LOGIN, 'password': UNITAL_PASS, 'doaction': 'loginformaction', 'viewType': 'html'}
    response = requests.post(UNITAL_BASE_URL, data=params)
    return response.cookies.get('JSESSIONID')
