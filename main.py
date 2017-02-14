# -*- coding: utf-8 -*-
import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.insert(0, 'libs')

#웹 크롤링 관련 라이브러리 로드
import mechanize
from bs4 import BeautifulSoup as bs, NavigableString, Tag

#현재 날짜 라이브러리 로드
import datetime as dt

# 구글 앱 엔진 라이브러리 로드
from google.appengine.api import urlfetch
from google.appengine.ext import ndb
import webapp2

# URL, JSON, 로그, 정규표현식 관련 라이브러리 로드
import urllib
import urllib2
import json
import logging
import re

# 봇 토큰, 봇 API 주소
TOKEN = 'Your Telegram Bot Token'
BASE_URL = 'https://api.telegram.org/bot' + TOKEN + '/'

# 봇이 응답할 명령어
CMD_START     = '/start'
CMD_STOP      = '/stop'
CMD_HELP      = '/help'

CMD_WEATHER = u'/날씨'
CMD_RT = u'/실시간'
CMD_FOOTBALL = u'해축'

# 봇 사용법 & 메시지
USAGE = u"""[사용법] 아래 명령어를 메시지로 보내거나 버튼을 누르시면 됩니다.
/start - (봇 활성화)
/stop  - (봇 비활성화)
/help  - (이 도움말 보여주기)
"""
MSG_START = u"""이지오의 개인 비서 봇입니다.
수행할 명령을 입력하여주세요.

1. /날씨 지역 : 입력한 지역의 날씨를 알려줍니다.
2. /실시간 : 현재 네이버의 실시간 검색어 리스트를 알려줍니다.
3. /해축 : 오늘 일자의 해외축구 중계/결과를 알려줍니다."""

MSG_STOP  = u'봇을 정지합니다.'

# 커스텀 키보드
CUSTOM_KEYBOARD = [
        [CMD_START],
        [CMD_STOP],
        [CMD_HELP],
        ]

# 채팅별 봇 활성화 상태
# 구글 앱 엔진의 Datastore(NDB)에 상태를 저장하고 읽음
# 사용자가 /start 누르면 활성화
# 사용자가 /stop  누르면 비활성화
class EnableStatus(ndb.Model):
    enabled = ndb.BooleanProperty(required=True, indexed=True, default=False,)

def set_enabled(chat_id, enabled):
    u"""set_enabled: 봇 활성화/비활성화 상태 변경
    chat_id:    (integer) 봇을 활성화/비활성화할 채팅 ID
    enabled:    (boolean) 지정할 활성화/비활성화 상태
    """
    es = EnableStatus.get_or_insert(str(chat_id))
    es.enabled = enabled
    es.put()

def get_enabled(chat_id):
    u"""get_enabled: 봇 활성화/비활성화 상태 반환
    return: (boolean)
    """
    es = EnableStatus.get_by_id(str(chat_id))
    if es:
        return es.enabled
    return False

def get_enabled_chats():
    u"""get_enabled: 봇이 활성화된 채팅 리스트 반환
    return: (list of EnableStatus)
    """
    query = EnableStatus.query(EnableStatus.enabled == True)
    return query.fetch()

# 메시지 발송 관련 함수들
def send_msg(chat_id, text, reply_to=None, no_preview=True, keyboard=None):
    u"""send_msg: 메시지 발송
    chat_id:    (integer) 메시지를 보낼 채팅 ID
    text:       (string)  메시지 내용
    reply_to:   (integer) ~메시지에 대한 답장
    no_preview: (boolean) URL 자동 링크(미리보기) 끄기
    keyboard:   (list)    커스텀 키보드 지정
    """
    params = {
        'chat_id': str(chat_id),
        'text': text.encode('utf-8'),
        }
    if reply_to:
        params['reply_to_message_id'] = reply_to
    if no_preview:
        params['disable_web_page_preview'] = no_preview
    if keyboard:
        reply_markup = json.dumps({
            'keyboard': keyboard,
            'resize_keyboard': True,
            'one_time_keyboard': False,
            'selective': (reply_to != None),
            })
        params['reply_markup'] = reply_markup
    try:
        urllib2.urlopen(BASE_URL + 'sendMessage', urllib.urlencode(params)).read()
    except Exception as e: 
        logging.exception(e)

# 봇 명령 처리 함수들
def cmd_start(chat_id):
    u"""cmd_start: 봇을 활성화하고, 활성화 메시지 발송
    chat_id: (integer) 채팅 ID
    """
    set_enabled(chat_id, True)
    send_msg(chat_id, MSG_START, keyboard=CUSTOM_KEYBOARD)

def cmd_stop(chat_id):
    u"""cmd_stop: 봇을 비활성화하고, 비활성화 메시지 발송
    chat_id: (integer) 채팅 ID
    """
    set_enabled(chat_id, False)
    send_msg(chat_id, MSG_STOP)

def cmd_help(chat_id):
    u"""cmd_help: 봇 사용법 메시지 발송
    chat_id: (integer) 채팅 ID
    """
    send_msg(chat_id, USAGE, keyboard=CUSTOM_KEYBOARD)

def search(chat_id, text):
    textEnter = text
    browser = mechanize.Browser()

    browser.set_handle_robots(False)
    browser.set_handle_referer(False)
    browser.addheaders = [('User-agent', 'Firefox')]

    browser.open("http://www.naver.com/")
    browser.select_form(nr=0)

    browser.form['query'] = textEnter + u"날씨"
    browser.submit()

    soup = bs(browser.response().read(), 'html.parser')

    weather = soup.find("div", class_='fl')

    send_msg(chat_id, u"현재 날씨를 알려줄게요")

    send_msg(chat_id, weather.contents[1].text)
    send_msg(chat_id, weather.contents[3].text)
    
    w1 = weather.contents[5].text
    w1 = w1.replace(u'도움말', '')
    send_msg(chat_id, w1)
    
    w2 = weather.contents[7].text
    w2 = w2.replace(u'닫기', '')
    send_msg(chat_id, w2)
    
    return

def real_time_keyword(chat_id):
    utcnow = dt.datetime.utcnow()
    now = utcnow + (dt.timedelta(hours=9))
    t = now.strftime(u'%Y년 %m월 %d일 %H시 %M분')

    send_msg(chat_id, t+u' 현재\n네이버 실시간 검색 Top20')
    browser = mechbrowser = mechanize.Browser()

    browser.set_handle_robots(False)
    browser.set_handle_referer(False)
    browser.addheaders = [('User-agent', 'Firefox')]

    browser.open("http://www.naver.com/")
    
    soup = bs(browser.response().read(), 'html.parser')

    keyword = soup.find_all("span", class_='ell')
    
    keyarr = ''        
   
    for i, key in enumerate(keyword):
        keyarr += str(i+1)+'위 : '+key.text+'\n'
    
    send_msg(chat_id, keyarr)

    return

def process_cmds(msg):
    u"""사용자 메시지를 분석해 봇 명령을 처리
    chat_id: (integer) 채팅 ID
    text:    (string)  사용자가 보낸 메시지 내용
    """
    msg_id = msg['message_id']
    chat_id = msg['chat']['id']
    text = msg.get('text')

    if (not text):
        return
    if CMD_START == text:
        cmd_start(chat_id)
        return
    if (not get_enabled(chat_id)):
        return
    if CMD_STOP == text:
        cmd_stop(chat_id)
        return
    if CMD_HELP == text:
        cmd_help(chat_id)
        return

    cmd_weather_match = re.match('^'+CMD_WEATHER+' (.*)', text)
    
    if CMD_RT == text:
        real_time_keyword(chat_id)
        return
    if cmd_weather_match:	     
        search(chat_id, cmd_weather_match.group(1))
        return
     
    send_msg(chat_id,u'명령을 제대로 입력해주세요.')
    return

# 웹 요청에 대한 핸들러 정의
# /me 요청시
class MeHandler(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        self.response.write(json.dumps(json.load(urllib2.urlopen(BASE_URL + 'getMe'))))

# /updates 요청시
class GetUpdatesHandler(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        self.response.write(json.dumps(json.load(urllib2.urlopen(BASE_URL + 'getUpdates'))))

# /set-wehook 요청시
class SetWebhookHandler(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        url = self.request.get('url')
        if url:
            self.response.write(json.dumps(json.load(urllib2.urlopen(BASE_URL + 'setWebhook', urllib.urlencode({'url': url})))))

# /webhook 요청시 (텔레그램 봇 API)
class WebhookHandler(webapp2.RequestHandler):
    def post(self):
        urlfetch.set_default_fetch_deadline(60)
        body = json.loads(self.request.body)
        self.response.write(json.dumps(body))
        process_cmds(body['message'])

# 구글 앱 엔진에 웹 요청 핸들러 지정
app = webapp2.WSGIApplication([
    ('/me', MeHandler),
    ('/updates', GetUpdatesHandler),
    ('/set-webhook', SetWebhookHandler),
    ('/webhook', WebhookHandler),
], debug=True)
