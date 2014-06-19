

#!/usr/bin/env python
# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
# Name:        utils
# Purpose:
#
# Author:      Administrator
#
# Created:     15/06/2014
# Copyright:   (c) Administrator 2014
# Licence:     <your licence>
#-------------------------------------------------------------------------------

import json
import urllib
import urllib2

import threading
__version__ = '0.1.0'
__author__ = 'Liang Cha (ckmx945@gmail.com)'

'''
Python client SDK for Micro Message Public Platform API.
'''



class APIError(StandardError):
    '''
    raise APIError if reciving json message indicating failure.
    '''
    def __init__(self, error_code, error_msg):
        self.error_code = error_code
        self.error_msg = error_msg
        StandardError.__init__(self, error_msg)

    def __str__(self):
        return 'APIError: %s:%s' %(self.error_code, self.error_msg)


class JsonDict(dict):
    ' general json object that allows attributes to bound to and also behaves like a dict '

    def __getattr__(self, attr):
        try:
            return self[attr]
        except KeyError:
            raise AttributeError(r"'JsonDict' object has no attribute '%s'" %(attr))

    def __setattr__(self, attr, value):
        self[attr] = value


def _parse_json(s):
    ' parse str into JsonDict '

    def _obj_hook(pairs):
        o = JsonDict()
        for k, v in pairs.iteritems():
            o[str(k)] = v
        return o
    return json.loads(s, object_hook = _obj_hook)


(_HTTP_GET, _HTTP_POST, _HTTP_FILE) = range(3)

def _decode_str(v):
    '''
    do url-encode v

    >>> _encode_params(R&D')
    'R%26D'
    '''
    if isinstance(v, basestring):
        qv = v if isinstance(v, unicode) else v.decode('utf-8')
        return  urllib.quote(qv)
    else:
        return None

def _encode_str(v):
    '''
    do url-encode v

    >>> _encode_params(R&D')
    'R%26D'
    '''
    if isinstance(v, basestring):
        qv = v.encode('utf-8') if isinstance(v, unicode) else v
        return  urllib.quote(qv)
    else:
        return None


def _encode_params(**kw):
    '''
    do url-encode parmeters

    >>> _encode_params(a=1, b='R&D')
    'a=1&b=R%26D'
    '''
    args = []
    body = None
    base_path = None
    for k, v in kw.iteritems():
        if k == 'body':
            body = v
            continue
        if k in ['pic']:
            continue
        if k  == 'base_path':
            base_path = v
            continue
        if isinstance(v, basestring):
            qv = v.encode('utf-8') if isinstance(v, unicode) else v
            args.append('%s=%s' %(k, urllib.quote(qv)))
        else:
            if v == None:
                args.append('%s=' %(k))
            else:
                qv = str(v)
                args.append('%s=%s' %(k, urllib.quote(qv)))
    return ('&'.join(args), body, base_path)


def _encode_multipart(**kw):
    ' build a multipart/form-data body with randomly generated boundary '
    boundary = '----------%s' % hex(int(time.time()) * 1000)
    data = []
    for k, v in kw.iteritems():
        if hasattr(v, 'read'):
            data.append('--%s' % boundary)
            filename = getattr(v, 'name', '')
            if filename == None or len(filename) == 0:
                filename = '/tmp/test.jpg'
            content = v.read()
            data.append('Content-Disposition: form-data; name="%s"; filename="%s"' % (k, filename))
            data.append('Content-Length: %d' % len(content))
            #data.append('Content-Type: application/octet-stream')
            data.append('Content-Type: image/jpeg')
            data.append('Content-Transfer-Encoding: binary\r\n')
            data.append(content)
            break
    data.append('--%s--\r\n' % boundary)
    return '\r\n'.join(data), boundary


def _http_call(the_url, method, token,  **kw):
    '''
    send an http request and return a json object  if no error occurred.
    '''
    params = None
    boundary = None
    body = None
    base_path = None
    (params, body, base_path) = _encode_params(**kw)
    if method == _HTTP_FILE:
        the_url = the_url.replace('https://api.', 'http://file.api.')
        body, boundary = _encode_multipart(**kw)
    if token == None:
        http_url = '%s?%s' %(the_url, params)
    else:
        the_url = the_url + '?access_token=' + token
        http_url = '%s&%s' %(the_url, params) if (method == _HTTP_GET or method == _HTTP_FILE) else the_url
    http_body = str(body) if (method == _HTTP_POST) else body

    req = urllib2.Request(http_url, data = http_body)

    if boundary != None:
        req.add_header('Content-Type', 'multipart/form-data; boundary=%s' % boundary)
    try:
##        resp = urllib2.urlopen(req, timeout = 5)
        resp = urllib2.urlopen(req, timeout=5)
        body = resp.read()

        try:
            rjson = _parse_json(body)

        except Exception, e:
            if resp.getcode() != 200:
                raise e
            filename = None
            if resp.headers['Content-Type'] == 'image/jpeg':
                filename = 'WX_%d.jpg' %(int(time.time()))
                if base_path == None:
                    base_path = './'
            else:
                raise e
            try:
                print '%s/%s' %(base_path, filename)
                fd = open('%s/%s' %(base_path, filename), 'wb')
                fd.write(body)
            except Exception, e:
                raise e
            fd.close()
            return _parse_json('{"path":"%s/%s"}' %(base_path, filename))
        if hasattr(rjson, 'errcode') and rjson['errcode'] != 0:
            raise APIError(str(rjson['errcode']), rjson['errmsg'])
        return rjson
    except urllib2.HTTPError, e:
        print 'urllib2.HTTPError:%s',e
        try:
            rjson = _parse_json(e.read())
        except:
            rjson = None
            if hasattr(rjson, 'errcode'):
                raise APIError(rjson['errcode'], rjson['errmsg'])
        raise e


class filecache:
    '''
    the information is temporarily saved to the file.
    '''
    def __init__(self, path, create = False):
        self.path = path
        self.dict_data = None
        fd = None
        try:
            fd = open(self.path, 'rb')
        except Exception, e:
            print 'filecache open error:', e
            if not create:
                return None
            else:
                fd = open(self.path, 'wb')
                fd.close()
                fd = open(self.path, 'rb')
        data = fd.read()
        if len(data) == 0:
            data = '{}'
        self.dict_data = eval(data)
        fd.close()

    def get(self, key):
        if self.dict_data.has_key(key):
            return self.dict_data[key]
        return None

    def set(self, key, value, time = 0):
        if self.dict_data.has_key(key):
            self.dict_data[key] = value
        else:
            self.dict_data.update({key:value})

    def delete(self, key, time = 0):
        if self.dict_data.has_key(key):
            del self.dict_data[key]

    def save(self):
        fd = open(self.path, 'wb')
        fd.write(repr(self.dict_data))
        fd.close()

    def __str__(self):
        data = []
        for key in self.dict_data.keys():
            data += ['"%s":"%s"' %(str(key), str(self.dict_data[key]))]
        return '{%s}' %(', '.join(data))

class _Executable(object):

    def __init__(self, client, method, path):
        self._client = client
        self._method = method
        self._path = path

    def __call__(self, **kw):
        try:
            return _http_call('%s%s' %(self._client.api_url, self._path), \
                self._method, self._client.access_token, **kw)
        except APIError,e:
            if e.error_code == 40001:
                print 'APIError and do request_access_token()'
                self._client.request_access_token()

                return _http_call('%s%s' %(self._client.api_url, self._path), \
                    self._method, self._client.access_token, **kw)


    def __str__(self):
        return '_Executable (%s)' %(self._path)

    __repr__ = __str__



class _Callable(object):

    def __init__(self, client, name):
        self._client = client
        self._name = name

    def __getattr__(self, attr):
        if attr == '_get':
            return _Executable(self._client, _HTTP_GET, self._name)
        if attr == 'post':
            return _Executable(self._client, _HTTP_POST, self._name)
        if attr == 'file':
            return _Executable(self._client, _HTTP_FILE, self._name)
        name = '%s/%s' %(self._name, attr)
        return _Callable(self._client, name)

    def __str__(self):
        return '_Callable (%s)' %(self._name)

def mkdir(path):
    import os

    path=path.strip()

    path=path.rstrip("\\")

    isExists=os.path.exists(path)

    if not isExists:

        os.makedirs(path)
        return True
    else:

        return False


def main():

##    mkpath="d:\\qttc\\web\\"
##    mkdir(mkpath)
    pass

if __name__ == '__main__':
    main()
