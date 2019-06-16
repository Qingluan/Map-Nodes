import sys,os
import argparse
import json
import sys, tempfile, os
from subprocess import call
from MapHack_src.remote import  run_server
from MapHack_src.remote import  Comunication
from MapHack_src.task import Task
from MapHack_src.log import L
from MapHack_src.init import init
from MapHack_src.daemon import daemon_exec
from MapHack_src.config import get_local_config, update

parser = argparse.ArgumentParser(usage="a controll node in server, can do some thing by controller. all use async to implement.")
parser.add_argument("-c","--conf", help="use config json  file ,format like ss.")
parser.add_argument("--updater", default=False, action='store_true', help="start updater")
parser.add_argument("-hh","--remote-help", default=False, action='store_true', help="show remote's help and app , must use -c [config.json]")
parser.add_argument("-d","--daemon", default=None, help="aciton start/restart/stop  [--updater] ")
parser.add_argument("-a","--app", nargs="*", help="set app name")
parser.add_argument("-l","--log", nargs="*", help="show log -l *args: -l app [line time] ")
parser.add_argument("-t","--as", default='ip', help="set args ip/host")
parser.add_argument("--time", default='', help="set time to queyr exm: '2019-9-18'")
parser.add_argument("--op", default='run', help="set args run/install/log/test")
parser.add_argument("-o","--option", default='', help="set option default: ''")
parser.add_argument("-S","--session", default='default', help="set option default: default")
parser.add_argument("-B","--not-background", default=True, action='store_false', help="send task not in background")
parser.add_argument("-T","--test", default=False, action='store_true', help="test client ")
parser.add_argument("--tree", default=False, action='store_true', help="show tree in session")
parser.add_argument("-i","--generate-sec-conf", default=False, action='store_true', help="initial json conf in server ")
parser.add_argument("--push-ini", default=None,  help="sync local ini to server.")
parser.add_argument("--vi-ini", default=False,action='store_true',  help="change ini file in server.")
parser.add_argument("--init", default=None,  help="init remote by ssh : --init root@server.com:10022")


def editor(content):
    EDITOR = os.environ.get('EDITOR','vim') #that easy!
    with tempfile.NamedTemporaryFile(suffix=".tmp") as tf:
        tf.write(content.encode())
        tf.flush()
        call([EDITOR, tf.name])

  # do the parsing with `tf` using regular File operations.
  # for instance:
        tf.seek(0)
        edited_message = tf.read()
        return edited_message.decode()

def main():
    args = parser.parse_args()
    w = None
    conf = get_local_config()
    #if 'last_session' not in list(conf['client'].keys()):
    #    update('client','last_session', args.session)
    #    conf = get_local_config()
    #else:
    #    update('client','last_session', args.session)

    #if 'last_op' not in list(conf['client'].keys()):
    #    update('client','last_op', args.op)
    #    conf = get_local_config()
    #
    #if 'last_app' not in list(conf['client'].keys()):
    #    if not args.app:
    #        app = ''
    #    else:
    #        app = args.app[0]
    #    update('client','last_app', app)
    #    conf = get_local_config()

    #last_session = conf['client']['last_session']
    #last_app = conf['client']['last_app']
    #last_op = conf['client']['last_op']
    #if '-s' not in sys.argv:
    #    args.session = last_session
    #if '--op' not in sys.argv and '-l' not in sys.argv :
    #    args.op = last_op

    L('session: ', args.session, 'op: ',args.op)

    if args.generate_sec_conf:
        d = {}
        ip = [i.strip() for i in os.popen("ifconfig").read().split("\n") if 'inet' in i and '127.0.0.1' not in i and '::' not in i][0].split()[1]
        print("server ip: %s" % ip)
        for k in ['server_port','password', 'method']:
            v = input(k)
            if not v:
                raise Exception("%s : must a val"% k)
            d[k] = v
        d['server'] = ip
        with open("seed-node-server.json", "w") as fp:
            json.dump(d, fp)
        sys.exit(0)
    if args.conf:
        f = args.conf
        with open(f) as fp:
            w = json.load(fp)
            assert  'server' in w
            assert  'server_port' in w
            assert  'password' in w
            assert  'method' in w

    if args.daemon:
        if args.updater:
            if args.daemon == 'start':
                assert  w is not None
                daemon_exec(pid_file="/var/run/hack-updater.pid",log_file="/var/log/hack-updater.log")
                w['server_port'] = str(int(w['server_port']) + 1)
                w['server'] = 'localhost'
                run_server(w)
            elif args.daemon == 'stop':

                daemon_exec(command='stop', pid_file='/var/run/hack-updater.pid',log_file='/var/log/hack-updater.log')
                run_server(w)
        else:
            if args.daemon == 'start':
                assert  w is not None
                daemon_exec()
                run_server(w)
            elif args.daemon == 'stop':
                daemon_exec(command='stop')
                run_server(w)

    if args.push_ini and os.path.exists(args.push_ini):
        with open(args.sync_ini) as fp:
            content = fp.read()
        data = Task.build_json('', op="sync-ini", session=args.session, content=content)
        res = Comunication.SendOnce(w, data)
        L(res[2]['reply'])
        sys.exit(0)

    if args.vi_ini:
        data = Task.build_json('', op='get-ini', session=args.session, **{'option':args.option, 'background':args.not_background, 'date': args.time})
        res = Comunication.SendOnce(w, data)
        L(res[2]['reply'])
        content = editor(res[2]['reply'])
        data = Task.build_json('', op="sync-ini", session=args.session, content=content)
        res = Comunication.SendOnce(w, data)
        try:
            L(res[2]['reply'])
        except Exception:
            L(res[2])

        if os.path.exists("/tmp/tmp.ini"):
            os.remove('/tmp/tmp.ini')
        sys.exit(0)



    if args.app:
        # args.op = 'run'
        if len(args.app) == 1:
            target = ''
        else:
            target = args.app[1]
        app = args.app[0]
        if args.op.strip() == 'install':
            args.session = 'config'
        data = Task.build_json(app, op=args.op, session=args.session, **{getattr(args,'as'): target, 'option':args.option, 'background':args.not_background, 'date': args.time})
        res = Comunication.SendOnce(w, data)
        try:
            L(res[2]['reply'])
            sys.exit(0)
        except Exception as e:
            L(res[2])
            sys.exit(1)
            
    if args.log:
        args.op = 'log'
        args.app = args.log[0]
        app = args.log[0]
        if len(args.log) == 2:
            lines = args.log[1]
            time = args.time
        elif len(args.log) == 3:
            lines = args.log[1]
            time = args.log[2]
        else:
            lines = '50'
            time = args.time
        
        data = Task.build_json(app,op='log', session=args.session, **{'option':args.option, 'background':args.not_background, 'date': time, 'line':lines})
        res = Comunication.SendOnce(w, data)
        try:
            L(res[2]['reply'])
            sys.exit(0)
        except Exception as e:
            L(res[2])
            sys.exit(1)


    if args.op != 'run':
        if args.app:
            app = args.app[0]
        else:
            app = ''
        if args.op.strip() == 'install':
            args.session = 'config'
        # L("session:",args.session)
        data = Task.build_json(app,op=args.op, session=args.session, **{'option':args.option, 'background':args.not_background, 'date': args.time})
        res = Comunication.SendOnce(w, data)
        try:
            L(res[2]['reply'])
            sys.exit(0)
        except Exception as e:
            L(res[2])
            sys.exit(1)


    if args.test:
        data = Task.build_json("", session=args.session, op="test")
        res = Comunication.SendOnce(w, data)
        L(res[2]['reply'])
        sys.exit(0)

    if args.remote_help:
        data = Task.build_json('',op='ls', session=args.session, **{'option':args.option, 'background':args.not_background, 'date': args.time})
        res = Comunication.SendOnce(w, data)
        try:
            L(res[2]['reply'])
            sys.exit(0)
        except Exception as e:
            L(res[2])
            sys.exit(1)


    if args.init:
        init(args.init)
        sys.exit(0)

    if args.tree:
        data = Task.build_json('tree',op='run', session=args.session, **{getattr(args,'as'): '/tmp/tasks','option':args.option, 'background':False, 'date': args.time})
        res = Comunication.SendOnce(w, data)
        try:
            L(res[2]['reply'])
            sys.exit(0)
        except Exception as e:
            L(res[2])
            sys.exit(1)







if __name__ == "__main__":
    main()
