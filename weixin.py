#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time

from utils import filecache
from utils import _http_call, _HTTP_GET, _HTTP_POST, _HTTP_FILE
from utils import _Callable

try:
    import memcache
except Exception, e:
    print '\033[95mWrining: %s. use local filecache.\033[0m' %e

import sqlobject
from Connection import conn

class User(sqlobject.SQLObject):
    _connection = conn
    name = sqlobject.UnicodeCol(length=255, unique=True)

    mode = sqlobject.StringCol(length=255, default='geci')
    geci = sqlobject.StringCol(length=1020, default=None)
    #new add field

User.createTable(ifNotExists=True)

def _DB_getUserByName(name):

    users = User.select(User.q.name == name)
##    print lyrics
    if (users.count() > 0):
        return users[0]
    else:
        return None

def _DB_addUserByName(u_name):
    try:

        return User(name = u_name)

    except Exception, e:
        print '_DB_addUserByDict:%s'%e
        return None

def getUserByName(name):
    user = _DB_getUserByName(name)

    return user if user else _DB_addUserByName(name)

class WeiXinClient(object):
    '''
    API clinet using synchronized invocation.

    >>> fc = False
    'use memcache save access_token, otherwise use filecache, path=[file_path | ip_addr]'
    '''
    def __init__(self, appID, appsecret, fc = False, path = '127.0.0.1:11211'):
        self.api_url = 'https://api.weixin.qq.com/cgi-bin/'
        self.app_id = appID
        self.app_secret = appsecret
        self.access_token = None
        self.expires = 0
        self.fc = fc
        if not self.fc:
            self.mc = memcache.Client([path], debug = 0)
        else:
            self.mc = filecache('%s/access_token' %(path), True)

    def request_access_token(self):
        token_key = 'access_token_%s' %(self.app_id)
        expires_key = 'expires_%s' %(self.app_id)
        access_token = self.mc.get(token_key)
##        print 'request_access_token:',access_token
        expires = self.mc.get(expires_key)
        if access_token == None or expires == None or \
                int(expires) < int(time.time()):
            rjson =_http_call(self.api_url + 'token', _HTTP_GET, \
                None, grant_type = 'client_credential', \
                appid = self.app_id, secret = self.app_secret)
            self.access_token = str(rjson['access_token'])
            expires_in = int(rjson['expires_in'])

            print 'new access_token:' , self.access_token
            print 'expires_in:' , expires_in

            self.expires = int(time.time()) + expires_in
            self.mc.set(token_key, self.access_token, \
                    time = self.expires - int(time.time()))
            self.mc.set(expires_key, str(self.expires), \
                    time = self.expires - int(time.time()))
            if self.fc:
                self.mc.save()

##            #提前60秒定时执行request_access_token
##            time_interval = expires_in - 60
##            print 'time_interval:' + time_interval
##            t = Timer(time_interval, request_access_token)
##            t.start()


        else:
            self.access_token = str(access_token)
            self.expires = int(expires)

    def del_access_token(self):
        token_key = 'access_token_%s' %(self.app_id)
        expires_key = 'expires_%s' %(self.app_id)
        self.access_token = None
        self.expires = 0
        if self.mc.fc:
            pass
        else:
            self.mc.delete(token_key)
            self.mc.delete(expires_key)

    def set_access_token(self, token, expires):
        self.access_token = token
        self.expires = expires

    def is_expires(self):
        return not self.access_token or time.time() > self.expires

    def __getattr__(self, attr):
        return _Callable(self, attr)

    def __str__(self):
        return 'url=%s\napp_id=%s\napp_secret=%s\naccess_token=%s\nexpires=%d' \
            %(self.api_url, self.app_id, self.app_secret, self.access_token, self.expires)







def test():
    ' test the API '
    wc = WeiXinClient('your_appid', \
                'your_secret', fc = True, path = '.')
##    wc.set_access_token("123456789abc", "60")
##    print wc.user.info._get(openid='obMnLt43lgfeeC8Ljn4-cLixEW6Q', lang='zh_CN')
    pass

if __name__ == '__main__':
    test()
