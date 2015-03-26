import requests, json
from urllib import urlencode
import xml.etree.ElementTree as ET

url = 'http://e.unitalm.ru/mkc/Do?'
login = '1547'
password = 'B^9sG7My'

#try to login
params = {'user': login, 'password': password, 'doaction': 'loginformaction', 'viewType': 'html'}
r = requests.post(url, data=params)
sessionId = r.cookies.get('JSESSIONID')

#fetch available courses
cookies = dict(JSESSIONID=sessionId)
getCoursesParams = {'doaction': 'Grid', 'gridname': 'mymeasureschildgrid', 'type': 'mymeasureschild'}
r = requests.post(url, data=getCoursesParams, cookies=cookies)
jsonResponse = json.loads(r.text)

#TODO select course by id or name (for now we take first course from list)
meid = jsonResponse['dataset'][0]['meid']
memberid = jsonResponse['dataset'][0]['memberid']

#fetch real course id
getCourseIdParams = {'meId' : meid, 'doaction' : 'LaunchStudentCourseFromSection'}
r = requests.post(url, data=getCourseIdParams, cookies=cookies)
root = ET.fromstring(r.text.encode('utf-8'))

#select "script" xml child
courseId = json.loads(root[2].text)['params']['id']

#find iframe url
getIframeParams = {'id' : courseId, 'mmid' : memberid, 'type' : 'viewcontent', 'doaction' : 'Go', 'ssectiontype' : 'modulecontentsection'}
r = requests.get(url + urlencode(getIframeParams), cookies=cookies)
iframeUrl = json.loads(r.text)['items'][5]['items'][0]['body']['body']['action']['url']

print iframeUrl

