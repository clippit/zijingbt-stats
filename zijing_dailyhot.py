#! /usr/bin/python
# -*- coding:utf-8 -*-

import sys
import urllib2
import urllib
import cookielib

from datetime import date, timedelta
from pyquery import PyQuery as pq

LOGIN_USERNAME = 'yourusername'
LOGIN_PASSWORD = 'yourpassword'
LOGIN_URL = "http://zijingbt.njuftp.org/login.html"
TORRENTS_LIST_URL = "http://zijingbt.njuftp.org/index.html?sort=24&per_page=200&page="
TALK_URL = "http://zijingbt.njuftp.org/talk.html"

##############################################################################
reload(sys)
sys.setdefaultencoding('utf-8')

cj = cookielib.CookieJar()
opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
urllib2.install_opener(opener)


def do_login():
    login_fields = {
        'username': LOGIN_USERNAME,
        'password': LOGIN_PASSWORD,
        'submit_login_button': u"登录".encode("UTF-8")
    }
    content_type, body = encode_multipart_formdata(login_fields)
    headers = {
        'Content-Type': content_type,
        'Content-Length': str(len(body))
    }
    req = urllib2.Request(LOGIN_URL, body, headers)
    res = urllib2.urlopen(req)
    assert res.getcode() == 200


def encode_multipart_formdata(fields):
    """
    fields is a sequence of (name, value) elements for regular form fields.
    Return (content_type, body) ready for request
    """
    BOUNDARY = '----------ThIs_Is_tHe_bouNdaRY_$'
    CRLF = '\r\n'
    L = []
    for (key, value) in fields.iteritems():
        L.append('--' + BOUNDARY)
        L.append('Content-Disposition: form-data; name="%s"' % key)
        L.append('')
        L.append(value)
    L.append('--' + BOUNDARY + '--')
    L.append('')
    body = CRLF.join(L)
    content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
    return content_type, body


def to_bytes(size_str):
    """
    an utility that convert KB, MB, GB filesize into bytes unit
    """
    size, unit = size_str.split(' ')
    assert unit in ('B', 'KB', 'MB', 'GB')
    convert_map = {
        'B': lambda i: long(i),
        'KB': lambda i: long(float(i) * 1024),
        'MB': lambda i: long(float(i) * 1024 * 1024),
        'GB': lambda i: long(float(i) * 1024 * 1024 * 1024)
    }
    return convert_map[unit](size)


def parse_list(torrent_list, normal_torrent_list=False):
    """
    filter torrent list according stat_date
    and parse torrent id, completed number and torrent size of each one
    then store them in stat_list

    if normal_torrent_list is True, it will return
    whether stop parsing on this page(False) or continue to next page(True)
    """
    if not torrent_list:
        return
    for e in torrent_list:
        node = pq(e)
        datestr = node('.index_date').text()[:10]
        torrent_date = date(int(datestr[:4]), int(datestr[5:7]), int(datestr[8:]))
        if torrent_date == stat_date:
            torrent_id = node.attr('onmouseover')[-8:-3]
            completed = int(node('td.index_number').text())
            size = to_bytes(node('.index_bytes').remove('.file').text())
            stat_list.append((torrent_id, completed, size))
        else:
            if normal_torrent_list and torrent_date < stat_date:
                return False
    if normal_torrent_list:  # check the last torrent of this page
        return True if torrent_date == stat_date else False


def send_stat(tweet):
    data = urllib.urlencode({'talk': tweet.encode('UTF-8')})
    res = urllib2.urlopen(TALK_URL, data)
    assert res.getcode() == 200


if __name__ == '__main__':
    do_login()
    page = 0
    stat_date = date.today() - timedelta(1)
    stat_list = []

    d = pq("%s%s" % (TORRENTS_LIST_URL, page))
    parse_list(d("tr.top_global:even"))
    parse_list(d("tr.top:even"))
    parse_list(d("tr.top_float:even"))
    while parse_list(d("tr.normal:even"), True):
        page += 1
        d = pq("%s%s" % (TORRENTS_LIST_URL, page))

    stat_list.sort(key=lambda i: i[1], reverse=True)
    daily_count = len(stat_list)
    total_completed = sum([i[1] for i in stat_list])
    total_size = sum([i[2] for i in stat_list])
    total_size_in_gb = '%.2f GB' % (total_size / 1024. / 1024 / 1024)
    top5 = [i[0] for i in stat_list[:5]]

    tweet = u"#每日热种# 紫荆%s发布了%s个资源，总大小%s，共计%s次完成下载。当日最热门资源: #种子%s# #种子%s# #种子%s# #种子%s# #种子%s#" % (
            stat_date.strftime(u"%m月%d日"),
            daily_count,
            total_size_in_gb,
            total_completed,
            top5[0], top5[1], top5[2], top5[3], top5[4], )
    send_stat(tweet)
