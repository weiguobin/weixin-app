#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Filename:     weixind.py
# Author:       Liang Cha<ckmx945@gmail.com>
# CreateDate:   2014-05-15

import os
import web
import time
import hashlib
import urllib
import urllib2
import thread
import re
##from lxml import etree
from xml.etree import ElementTree

from weixin import WeiXinClient
from lyric import LyricClient, Lyric

from weixin import getUserByName
#from yeelink import YeeLinkClient



_TOKEN = '352202198801050537'
_URLS = (
    '/*', 'weixinserver',
)

Custon_send_text_data_template  = '{"touser":"%(touser)s", "msgtype":"text", "text":{ "content":"%(content)s"}}'

def _check_hash(data):
    signature = data.signature
##    print 'signature:',signature
    timestamp = data.timestamp
    nonce = data.nonce
    list = [_TOKEN, timestamp, nonce]
    list.sort()
    sha1 = hashlib.sha1()
    map(sha1.update, list)
    hashcode = sha1.hexdigest()
##    print 'hashcode:',hashcode
    if hashcode == signature:
        return True
    return False

def _get_user_info(wc):
    req = wc.user.get._get(next_openid = None)
    count = req.count
    total = req.total
    data = req.data
    id_list = data.openid
    while count < total:
        if next_openid in data.openid:
            break
        req = wc.user.get._get(next_openid = None)
        count += req.count
        data = req.data
        next_openid = req.next_openid
        id_list.extend(data.openid)
    info_list = []
    for open_id in id_list:
        req = wc.user.info._get(openid=open_id, lang='zh_CN')
        name ='%s' %(req.nickname)
        place = '%s,%s,%s' %(req.country, req.province, req.city)
        sex = '%s' %(u'男') if (req.sex == 1) else u'女'
        info_list.append({'name':name, 'place':place, 'sex':sex})
    return info_list


def _arduino_client(data):
    import select
    import socket
    c = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    c.setblocking(False)
    inputs = [c]
    c.connect(('192.168.1.20', 6666))
    c.sendall(data)
    readable, writeable, exceptional = select.select(inputs, [], [], 2)
    if not readable:
        return '{"errno": -1, "msg":"wait response timeout."}'
    else:
        return c.recv(1024)


def _take_snapshot(addr, port, client):
    url = 'http://%s:%d/?action=snapshot' %(addr, port)
    req = urllib2.Request(url)
    try:
        resp = urllib2.urlopen(req, timeout = 2)
    except urllib2.HTTPError, e:
        print e
        return  None
    return client.media.upload.file(type='image', pic=resp)


def _do_event_subscribe(server, fromUser, toUser, doc):
    words = u'''当前为搜歌词模式， 请输入 【歌曲名】
    或者 【歌曲名】 【歌手】 搜索指定的歌词 ！ '''
    return server._reply_text(fromUser, toUser, words)


def _do_event_unsubscribe(server, fromUser, toUser, doc):
    return server._reply_text(fromUser, toUser, u'bye!')


def _do_event_SCAN(server, fromUser, toUser, doc):
    pass


def _do_event_LOCATION(server, fromUser, toUser, doc):
    pass


def _do_event_CLICK(server, fromUser, toUser, doc):
    key = doc.find('EventKey').text
    try:
        return _weixin_click_table[key](server, fromUser, toUser, doc)
    except KeyError, e:
        print '_do_event_CLICK: %s' %e
        return server._reply_text(fromUser, toUser, u'Unknow click: '+key)


_weixin_event_table = {
    'subscribe'     :   _do_event_subscribe,
    'unsbscribe'    :   _do_event_unsubscribe,
    'SCAN'          :   _do_event_SCAN,
    'LOCATION'      :   _do_event_LOCATION,
    'CLICK'         :   _do_event_CLICK,
}


def _do_click_V1001_USER_LIST(server, fromUser, toUser, doc):
    reply_msg = ''
    user_list = _get_user_info(server.client)
    for user in user_list:
        reply_msg += '%s|%s|%s\n' %(user['name'], user['place'], user['sex'])
    return server._reply_text(fromUser, toUser, reply_msg)


def _do_click_V1001_YELLOW_CHICK(server, fromUser, toUser, doc):
    pass


def _do_click_V1001_GOOD(server, fromUser, toUser, doc):
    pass


def _do_click_V1001_LED_ON(server, fromUser, toUser, doc):
    data = '{"name":"digitalWrite", "para":{"pin":7, "value":1}}'
    buf = _arduino_client(data)
    errno = eval(buf)['errno']
    reply_msg = None
    if errno == 0:
        reply_msg = '成功点亮'
    elif errno == -1:
        reply_msg = eval[buf]['msg']
    else:
        reply_msg = '点亮失败'
    return server._reply_text(fromUser, toUser, reply_msg)


def _do_click_V1001_LED_OFF(server, fromUser, toUser, doc):
    data = '{"name":"digitalWrite", "para":{"pin":7, "value":0}}'
    buf = _arduino_client(data)
    errno = eval(buf)['errno']
    reply_msg = None
    if errno == 0:
        reply_msg = '成功关闭'
    elif errno == -1:
        reply_msg = eval[buf]['msg']
    else:
        reply_msg = '关闭失败'
    return server._reply_text(fromUser, toUser, reply_msg)


def _dew_point_fast(t, h):
    import math
    a = 17.27
    b = 237.7
    temp = (a * t) / (b + t) + math.log(h / 100);
    td = (b * temp) / (a - temp);
    return td


def _do_click_SNAPSHOT(server, fromUser, toUser, doc):
    data = _take_snapshot('192.168.1.10', 24567, server.client)
    if data == None:
        return server._reply_text(fromUser, toUser, 'snapshot fail.')
    return server._reply_image(fromUser, toUser, data.media_id)


def _do_click_V1001_TEMPERATURES(server, fromUser, toUser, doc):
    data = '{"name":"environment", "para":{"pin":2}}'
    buf = _arduino_client(data)
    data = eval(buf)
    errno = data['errno']
    reply_msg = None
    if errno == 0:
        t = data['resp']['t']
        h = data['resp']['h']
        td = _dew_point_fast(t, h)
        reply_msg = "室内温度: %.2f℃\n室内湿度: %.2f\n室内露点: %.2f" %(t, h, td)
    else:
        reply_msg = data['msg']
    return server._reply_text(fromUser, toUser, reply_msg)


_weixin_click_table = {
    'V1001_USER_LIST'       :   _do_click_V1001_USER_LIST,
    'V1001_YELLOW_CHICK'    :   _do_click_V1001_YELLOW_CHICK,
    'V1001_LED_ON'          :   _do_click_V1001_LED_ON,
    'V1001_LED_OFF'         :   _do_click_V1001_LED_OFF,
    'V1001_TEMPERATURES'    :   _do_click_V1001_TEMPERATURES,
    'V1001_GOOD'            :   _do_click_V1001_GOOD,
    'V1001_SNAPSHOT'        :   _do_click_SNAPSHOT
}



class weixinserver:

    def __init__(self):
        self.app_root = os.path.dirname(__file__)
        self.templates_root = os.path.join(self.app_root, 'templates')
        self.render = web.template.render(self.templates_root)
        self.client = WeiXinClient('wxe3da4718bc1a9a18', \
                '2238eb7e0a13748039ec31f0309bbf68', fc = True, path = '.')

        self.client.request_access_token()

        self.lyric_client = LyricClient()
        #self.yee = YeeLinkClient('yee_key')

    def _downLoad_lyric_thread(self, fromUser, toUser, text_content):

        lyric = None
        song = ''

        if isinstance(text_content, tuple):
            song, artist_name = text_content
            lyrics = self.lyric_client.getLyricsBySongnameFromHttp(song, artist_name)
            if (len(lyrics) >= 1):
                lyric = lyrics[0]
        elif isinstance(text_content, Lyric):
            lyric = text_content
            song = lyric.song
        elif isinstance(text_content, unicode) or isinstance(text_content, str):
            reply_content = Custon_send_text_data_template % {'touser':fromUser, 'content':text_content}
            self.client.message.custom.send.post(body=reply_content)
            thread.exit_thread()
            return

        if isinstance(song, unicode):
            song = song.encode('utf-8')

        if lyric:
            try:

                text_content = self.lyric_client.downLoad_lyric(lyric)
            except Exception, e:
                text_content = '找不到歌曲:%s'%song

        else:

            text_content = '找不到歌曲:%s'%song

        reply_content = Custon_send_text_data_template % {'touser':fromUser, 'content':text_content}

        self.client.message.custom.send.post(body=reply_content)

        thread.exit_thread()

    def _deal_with_text_impl(self, fromUser, toUser, content):

        p = re.compile(r'\s+')

        args = p.split(content.encode('utf8'))

        if args[0] == '':
            del args[0]

        if args[-1] == '':
            del args[-1]

        print 'args:', args

        user = getUserByName(fromUser)

        if user.mode == 'geci':

##            if len(args) == 1 and args[0].isdigit():
##                #用户选择一个歌词文件
##                text_content = self.lyric_client.do_deal_choiceForUser(user, int(args[0]))
##                text_content = text_content.decode('utf-8')

            if len(args) == 1 or len(args) == 2:
                #用歌手名和歌曲名来搜歌词目录
                song = args[0]
                artist_name = args[1] if len(args) == 2 else None
                text_content = self.lyric_client.doSearchBySongnameForUserFromLocal(user, song, artist_name)

                print type(text_content)

                if isinstance(text_content, unicode) or isinstance(text_content, str):

                    return text_content
                else:

                    thread.start_new_thread(self._downLoad_lyric_thread, (fromUser, toUser, text_content))
                    return '恭喜您是第一个搜索此歌词的达人，请耐心等候...'

##                text_content = text_content.encode('utf-8')

            else:
                return '输入参数不正确'

        return '当前不处于歌词模式'

##    def _deal_with_text_thread(self, fromUser, toUser, content):
##
##        text_content = self._deal_with_text_impl(fromUser, toUser, content)
##        reply_content = Custon_send_text_data_template % {'touser':fromUser, 'content':text_content}
####        print 'reply_content:',reply_content
##
##        print self.client.message.custom.send.post(body=reply_content)
##        thread.exit_thread()

    def _recv_text(self, fromUser, toUser, doc):
        content = doc.find('Content').text

        reply_msg = self._deal_with_text_impl(fromUser, toUser, content)

        return self._reply_text(fromUser, toUser, reply_msg)

    def _recv_event(self, fromUser, toUser, doc):
        event = doc.find('Event').text
        try:
            return _weixin_event_table[event](self, fromUser, toUser, doc)
        except KeyError, e:
            print '_recv_event: %s' %e
            return self._reply_text(fromUser, toUser, u'Unknow event: '+event)

    def _recv_image(self, fromUser, toUser, doc):
        url = doc.find('PicUrl').text
        req = urllib2.Request(url)
        try:
            resp = urllib2.urlopen(req, timeout = 2)
           # print self.yee.image.upload('10296', '16660', fd = resp)
        except urllib2.HTTPError, e:
            print e
            return self._reply_text(fromUser, toUser, u'upload fail.')
        view = 'http://www.yeelink.net/devices/10296'
        return self._reply_text(fromUser, toUser, u'upload to:'+view)

    def _recv_voice(self, fromUser, toUser, doc):
        cmd = doc.find('Recognition').text;
        if cmd is None:
            return self._reply_text(fromUser, toUser, u'no Recognition, no command');
        if cmd == u'开灯':
            return _do_click_V1001_LED_ON(self, fromUser, toUser, doc)
        elif cmd == u'关灯':
            return _do_click_V1001_LED_OFF(self, fromUser, toUser, doc)
        elif cmd == u'温度':
            return _do_click_V1001_TEMPERATURES(self, fromUser, toUser, doc)
        else:
            return self._reply_text(fromUser, toUser, u'Unknow command: ' + cmd);

    def _recv_video(self, fromUser, toUser, doc):
        pass

    def _recv_location(self, fromUser, toUser, doc):
        pass

    def _recv_link(self, fromUser, toUser, doc):
        pass

    def _reply_text(self, toUser, fromUser, msg):
        return self.render.reply_text(toUser, fromUser, int(time.time()), msg)

    def _reply_image(self, toUser, fromUser, media_id):
        return self.render.reply_image(toUser, fromUser, int(time.time()), media_id)

    def GET(self):
        data = web.input()
##        print 'get data:',data
        if _check_hash(data):
            return data.echostr

    def POST(self):
        str_xml = web.data()
        doc = ElementTree.fromstring(str_xml)
        msgType = doc.find('MsgType').text
        fromUser = doc.find('FromUserName').text
        toUser = doc.find('ToUserName').text
        if msgType == 'text':
            return  self._recv_text(fromUser, toUser, doc)
        if msgType == 'event':
            return self._recv_event(fromUser, toUser, doc)
        if msgType == 'image':
            return self._recv_image(fromUser, toUser, doc)
        if msgType == 'voice':
            return self._recv_voice(fromUser, toUser, doc)
        if msgType == 'video':
            return self._recv_video(fromUser, toUser, doc)
        if msgType == 'location':
            return self._recv_location(fromUser, toUser, doc)
        if msgType == 'link':
            return self._recv_link(fromUser, toUser, doc)
        else:
            return self._reply_text(fromUser, toUser, u'Unknow msg:' + msgType)



web.config.debug = False

application = web.application(_URLS, globals()).wsgifunc()



if __name__ == "__main__":

    #import wsgi
    from bottle import run
    run(app=application, host='0.0.0.0', port=80)

##    weixin_s = weixinserver()
##    str_xml = ''' <xml>
## <ToUserName><![CDATA[toUser]]></ToUserName>
## <FromUserName><![CDATA[fromUser]]></FromUserName>
## <CreateTime>1348831860</CreateTime>
## <MsgType><![CDATA[text]]></MsgType>
## <Content><![CDATA[ 龙的传人    ]]></Content>
## <MsgId>1234567890123456</MsgId>
## </xml>'''
##    doc = ElementTree.fromstring(str_xml)
##    weixin_s._recv_text("wgb", "me", doc)
##
##    import time
##    time.sleep(3)
##    content = raw_input("input:")
##
##    str_xml = ''' <xml>
## <ToUserName><![CDATA[toUser]]></ToUserName>
## <FromUserName><![CDATA[fromUser]]></FromUserName>
## <CreateTime>1348831860</CreateTime>
## <MsgType><![CDATA[text]]></MsgType>
## <Content><![CDATA[ 1  ]]></Content>
## <MsgId>1234567890123456</MsgId>
## </xml>'''
##    doc = ElementTree.fromstring(str_xml)
##    weixin_s._recv_text("wgb", "me", doc)
##
##    content = raw_input("input:")
