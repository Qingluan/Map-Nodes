
import json
import os
import re
import geoip2
import geoip2.database as gd
import asyncio
from random import shuffle
from MapHack_src.config import get_local_config
from MapHack_src.task import Task
from MapHack_src.remote import Comunication
from MapHack_src.log import L

CONF = get_local_config()
SERVER_DIR = os.path.expanduser(CONF['client']['server_dir'])
SERVER_INI = os.path.expanduser(CONF['client']['server_ini'])

def ip2geo(ip):
    if not os.path.exists(os.path.expanduser('~/geo/GeoLite2-City.mmdb')):
        os.system('mkdir -p $HOME/geo && wget -c -t 10 "https://geolite.maxmind.com/download/geoip/database/GeoLite2-City.tar.gz" -O- |tar -xz  -C $HOME && mv $HOME/GeoLite2-City_2019*/GeoLite2-City.mmdb $HOME/geo')
    ipdb = gd.Reader(os.path.expanduser('~/geo/GeoLite2-City.mmdb'))
    return ipdb.city(ip).country.name


def select(countr_or_ip):
    countr_or_ip = countr_or_ip.lower()
    if re.match('^\d{1,3}', countr_or_ip):
        for i in os.listdir(SERVER_DIR):
            if i.startswith(countr_or_ip):
                with open(os.path.join(SERVER_DIR, i)) as fp:
                    yield json.load(fp)
    else:
        for i in os.listdir(SERVER_DIR):
            country = ip2geo(i).lower()
            if countr_or_ip in country:
                with open(os.path.join(SERVER_DIR, i)) as fp:
                    yield json.load(fp)


async def save_ini(code,tag,reply):
    if code == 0:
        if 'ip'  not in reply:
            L(reply)
            return
        ip = reply['ip']
        assert ip is not None
        if 'reply' in reply :
            with open(os.path.join(SERVER_INI, ip), 'w') as fp:
                fp.write(reply['reply'])

            L({ip: 'updated'})
        else:
            L(reply)
    else:
        L(reply)

def pull_all_ini(confs):
    msg = Task.build_json('',op='get-ini', session='config')
    msgs = [msg.copy() for i in range(len(confs))]
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return Comunication.SendMul(confs, msgs, loop=loop, callback=save_ini)



def build_tasks(confs, targets=[], apps=[], op='run', session='default', background=True, **kargs):
    if op == 'run':
        assert isinstance(apps, list)
        assert len(apps) > 0
        assert isinstance(targets, list)
        assert len(targets) > 0
        if len(apps) > 1:
            for app in apps:
                for target in targets:
                    yield Task.build_json(app, op=op, session=session,ip=target, backgroun=background, option='', **kargs)
        else:
            for i in range(len(confs)):
                yield Task.build_json(apps[0], op=op, session=session,ip=targets[0], backgroun=background, option='', **kargs)
    else:
        if apps:
            if len(apps) > 1:
                for i in range(len(confs)):
                    for app in apps:
                        yield Task.build_json(app, op=op, session=session, backgroun=background, option='', **kargs)
            else:
                for i in range(len(confs)):
                    yield Task.build_json(apps[0], op=op, session=session, backgroun=background, option='', **kargs)
        else:
            for i in range(len(confs)):
                yield Task.build_json('', op=op, session=session, backgroun=background, option='', **kargs)


def run_tasks(confs, msgs, callback=None, random=True):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    if random:
        shuffle(msgs)
    # print(confs, msgs)
    return Comunication.SendMul(confs, msgs, loop=loop,callback=callback)
    

