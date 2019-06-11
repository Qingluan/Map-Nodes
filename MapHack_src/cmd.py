import sys,os
import argparse
import json
from MapHack_src.remote import  run_server
from MapHack_src.remote import  Comunication
from MapHack_src.task import Task
from MapHack_src.log import L

parser = argparse.ArgumentParser(usage="a controll node in server, can do some thing by controller. all use async to implement.")
parser.add_argument("-c","--conf", help="use config json  file ,format like ss.")
parser.add_argument("-s","--start", default=False, action='store_true', help="start server")
parser.add_argument("-a","--app", nargs="*", help="set app name")
parser.add_argument("-t","--as", default='ip', help="set args ip/host")
parser.add_argument("--time", default='', help="set time to queyr exm: '2019-9-18'")
parser.add_argument("--op", default='run', help="set args run/install/log/test")
parser.add_argument("-o","--option", default='', help="set option default: ''")
parser.add_argument("-S","--session", default='default', help="set option default: default")
parser.add_argument("-B","--not-background", default=True, action='store_false', help="send task not in background")
parser.add_argument("-T","--test", default=False, action='store_true', help="test client ")
parser.add_argument("-i","--generate-sec-conf", default=False, action='store_true', help="initial json conf in server ")
parser.add_argument("--sync-ini", default=None,  help="sync local ini to server.")

def main():
    args = parser.parse_args()

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
    w = None
    f = args.conf
    with open(f) as fp:
        w = json.load(fp)
        assert  'server' in w
        assert  'server_port' in w
        assert  'password' in w
        assert  'method' in w
    if args.start:
        run_server(w)
    assert  w is not None

    if args.sync_ini and os.path.exists(args.sync_ini):
        with open(args.sync_ini) as fp:
            content = fp.read()
        data = Task.build_json('', op="sync-ini", session=args.session, content=content)
        res = Comunication.SendOnce(w, data)
        L(res[2]['reply'])
        sys.exit(0)

    if args.app:
        if len(args.app) == 1:
            target = ''
        else:
            target = args.app[1]
        app = args.app[0]
        
        data = Task.build_json(app, op=args.op, session=args.session, **{getattr(args,'as'): target, 'option':args.option, 'background':args.not_background, 'date': args.time})
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




if __name__ == "__main__":
    main()
