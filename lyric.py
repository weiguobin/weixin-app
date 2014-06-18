#!/usr/bin/env python
# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
# Name:        lyric
# Purpose:      歌词
#
# Author:      weiguobin
#
# Created:     15/06/2014
# Copyright:   (c) weiguobin 2014
# Licence:     <your licence>
#-------------------------------------------------------------------------------

from utils import filecache
from utils import _http_call, _HTTP_GET, _HTTP_POST, _HTTP_FILE
from utils import _Callable, _encode_str, _decode_str
from utils import mkdir

##import urllib
import urllib2
import os
import re

##from weixind import APP_CWD

##import sys
##reload(sys)
##sys.setdefaultencoding('utf-8')

def str2unicode(str_):
    u_str  = 'u\'' + str_ +'\''
    #print u_str
    return eval( u_str )

try:
    import memcache
except Exception, e:
    print '\033[95mWrining: %s. use local filecache.\033[0m' %e

###### -------------- DB START-------------------------------

import sqlobject
from Connection import conn

class Artist(sqlobject.SQLObject):
    _connection = conn
    artist_id = sqlobject.IntCol(length=14, unique=True)
    name = sqlobject.UnicodeCol(length=255)
    lyrics = sqlobject.MultipleJoin('Lyric', joinColumn='artist_id')

    #new add field

Artist.createTable(ifNotExists=True)

class Lyric(sqlobject.SQLObject):
    _connection = conn
    sid = sqlobject.IntCol(length=14, unique=True)
    song = sqlobject.UnicodeCol(length=255)
    lrc = sqlobject.UnicodeCol(length=255)
    artist_id = sqlobject.ForeignKey('Artist')
    aid = sqlobject.IntCol(length=14)

    #new add field
    local_path = sqlobject.UnicodeCol(length=255, default=None)
    sizes = sqlobject.IntCol(default=None)
    source = sqlobject.UnicodeCol(default=None)
Lyric.createTable(ifNotExists=True)




def _DB_getArtistByArtist_id(artist_id):

    artist = Artist.select(Artist.q.artist_id == artist_id)
##    print lyrics
    if (artist.count() > 0):
        return artist[0]
    else:
        return None

def _DB_addArtistByDict(**kwargs):
    try:
        artist = _DB_getArtistByArtist_id(kwargs['artist_id'])
        return artist if artist else Artist(**kwargs)

##        return  Artist(**kwargs)
    except Exception, e:
        print '_DB_addArtistByDict:%s'%e
        return None






def _DB_getLyricsBySong(songName, artist_name = None):

    clause = (Lyric.q.song == songName)
    if artist_name:
        clause = sqlobject.AND(Lyric.q.song == songName, \
                               Lyric.q.artist_id == Artist.q.id, \
                               Artist.q.name == artist_name)
    ##    print songName

##    print Lyric.select(Lyric.q.song == songName).count()

    lyrics = Lyric.select(clause)
##    print lyrics.count()
##    print lyrics
    if (lyrics.count() > 0):
        return lyrics
    else:
        return None


def _DB_getLyricBySid(sid):

    lyrics = Lyric.select(Lyric.q.sid == sid)
##    print lyrics
    if (lyrics.count() > 0):
        return lyrics[0]
    else:
        return None

def _DB_addLyricByDict(**kwargs):
    try:
        lyric = _DB_getLyricBySid(kwargs['sid'])
        return lyric if lyric else Lyric(**kwargs)

##        return  Lyric(**kwargs)
    except Exception, e:
        print '_DB_addLyricByDict:%s'%e
        return None





###### -------------- DB END-------------------------------

class LyricClient(object):
    '''
    API clinet using synchronized invocation.

    >>> fc = False
    'use memcache save , otherwise use filecache, path=[file_path | ip_addr]'
    '''
    def __init__(self, fc = False, path = '127.0.0.1:11211'):
        self.api_url = 'http://geci.me/api/'
        self.source= u'歌词迷'
        self.access_token = None

        self.fc = fc
        if not self.fc:
            self.mc = memcache.Client([path], debug = 0)
        else:
            self.mc = filecache('%s/lyric_filecache' %(path), True)


    def __getattr__(self, attr):
        return _Callable(self, attr)

    def _getArtistByArtist_idFromHttp(self, artist_id):
        the_url = self.api_url+'artist'
##        print artist_id
        the_url += "/"
        the_url += str(artist_id)


        print "_getArtistByArtist_idFromHttp url:" + the_url
        rjson =_http_call(the_url, _HTTP_GET, None)

        return rjson

    def _getArtistByArtist_id(self, artist_id):

        artist = _DB_getArtistByArtist_id(artist_id)
        if artist:
            return artist

        try:
            rjson = self._getArtistByArtist_idFromHttp(artist_id)

            if rjson['code'] == 0:
                result = rjson['result']

                if result:
                    kwargs = {}
                    kwargs['artist_id'] = artist_id
                    kwargs['name'] = result['name']

                    artist = _DB_addArtistByDict(**kwargs)

##            print artist
            return artist

        except Exception, e:
            print "exception:%s"%e
            return artist


    def _getLyricsBySongnameFromHttp(self, songName, artist_name = None):
        the_url = self.api_url+'lyric'

        if songName is not None:
            songName =  _encode_str(songName)
            the_url += "/"
            the_url += songName

        if artist_name is not None:
            artist_name =  _encode_str(artist_name)
            the_url += "/"
            the_url += artist_name

        print "_getLyricsBySongnameFromHttp url:" + the_url
        rjson =_http_call(the_url, _HTTP_GET, None)

        return rjson


    def getLyricsBySongnameFromHttp(self, songName, artist_name = None):
        lyrics = []

        try:
            print 'run _getLyricsBySongnameFromHttp(songName, artist_name) ...'
            #把该songName的歌词条目下载到本地
            rjson = self._getLyricsBySongnameFromHttp(songName, artist_name)

            if rjson['code'] == 0:
                result = rjson['result']

                artist_dict = {}
                index = 1
                for kwargs in result:

                    artist_id = kwargs['artist_id']
                    del kwargs['artist_id']

                    artist = None

                    if artist_id in artist_dict.keys():
                        artist = artist_dict[artist_id]

                    else:
                        artist = self._getArtistByArtist_id(artist_id)
                        artist_dict[artist_id] = artist

                    kwargs['artist_id'] = artist
                    kwargs['source'] = self.source

                    lyric = _DB_addLyricByDict(**kwargs)

                    if lyric:

                        lyrics.append(lyric)
                        return lyrics

            return lyrics

        except Exception, e:
            print "exception:%s"%e
            return lyrics

    def _show_choicesForUser(self, lyrics):
        content = u""

        space_count = 8
        space = u' '

        content += u"序号"
        content += space*(space_count-2)

        content += u"歌名"
        content += space*(space_count-2)

        content += u"歌手"
        content += os.linesep

        artist_dict = {}
        space_content = space + u''
        index = 1;

        for lyric in lyrics:
            content += unicode(index)
            if (index < 10):
                content += space*(space_count-1)
            else:
                content += space*(space_count-2)

            content += lyric.song
            content += space*(space_count-len(lyric.song))

            artist = lyric.artist_id
            content += artist.name
            content += os.linesep

            index += 1

        return content

    def doSearchBySongnameForUserFromLocal(self, user, songName, artist_name = None):

        # 从本地数据库查找
        lyrics = _DB_getLyricsBySong(songName, artist_name)
        if lyrics is None:
            return (songName, artist_name)

        lyric = lyrics[0]
        if lyric:
            try:
                if lyric.local_path and lyric.local_path != u'':

                    return self._read_lyric_from_local(lyric)

                else:
##                        self._downLoad_lyric(lyric)
                    return  lyric


            except Exception, e:
                print "deal_choice_ForUser:%s"%e
                return lyric




    def downLoad_lyric(self, lyric):
##        print 'downLoad_lyric'
        cwd = os.getcwd()
        print 'lyric.lrc:',lyric.lrc
        url = lyric.lrc

        p = re.compile(r'lrc/(\w+)/(\w+)/(\S+)')
        m = p.search(url)
        #m = re.search(r"lrc/(\w+)/(\w+)/(\S+)", url)

        lyric_save_path = u'www/'
        lyric_save_path += m.group(0)

        mkdir(os.path.dirname(lyric_save_path))

        lyric_content = ""

        f = urllib2.urlopen(url)

        data = f.read()

        lyric_save_absolute_path = os.path.join(cwd,lyric_save_path)
##        print 'downLoad_lyric lyric_save_absolute_path:',lyric_save_absolute_path

        with open(lyric_save_absolute_path, "wb") as code:
            code.write(data)
            lyric_content += data

        lyric.local_path = lyric_save_path
        lyric.sizes = len(data)

        return lyric_content


    def _read_lyric_from_local(self, lyric):
        print '_read_lyric_from_local'
        cwd = os.getcwd()
##        print 'os.getcwd:',cwd

        lyric_content = ""

        lyric_save_absolute_path = os.path.join(cwd,lyric.local_path)
        print '_read_lyric_from_local lyric_save_absolute_path:',lyric_save_absolute_path

        with open(lyric_save_absolute_path, "rb") as code:
            data = code.read()
            lyric_content += data

##        print "local read:\n" + lyric_content
        return lyric_content


    def do_deal_choiceForUser(self, user, choice):
        print 'do_deal_choiceForUser'
        if user.mode == 'geci':
            if not isinstance(choice, int):
                return None
            if user.geci is None or user.geci == '':
                return ''
            geci_map = eval(user.geci)
            if geci_map.has_key(choice):
                sid = geci_map[choice]

                lyric = _DB_getLyricBySid(sid)

                if lyric:
##                    print ' lyric.local_path:', lyric.local_path
##                    print ' lyric.local_path:', type(lyric.local_path)
                    try:
                        if lyric.local_path and lyric.local_path != u'':

                            return self._read_lyric_from_local(lyric)

                        else:

                            return self._downLoad_lyric(lyric)

                    except Exception, e:
                        print "deal_choice_ForUser:%s"%e
                        return None

            return None

        else:
            return None


def main():

    lyric_client = LyricClient()
    #http://geci.me/api/lyric/:song
    song = u"海阔天空"
    artist = u"Beyond"

    from weixin import getUserByName
    user = getUserByName(u'11')
    text = lyric_client.doSearchBySongnameForUser(user, song, artist)
    print type(text)
##    print user.geci

    lyric_client.do_deal_choiceForUser(user, 1)



if __name__ == '__main__':
    main()
