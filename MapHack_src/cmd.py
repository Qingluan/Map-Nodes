import argparse
import json
from MapHack_src.remote import  run_server
from MapHack_src.remote import  Comunication
from MapHack_src.task import Task

parser = argparse.ArgumentParser(usage="Manager project, can create git , sync , encrypt your repo")
parser.add_argument("-i","--init", help="default to initialize a projet in current dir")
parser.add_argument("-c","--conf", help="use config json  file ,format like ss.")
parser.add_argument("-s","--start", default=False, aciton='store_true', help="start server")
parser.add_argument("-a","--app", nargs="*", help="set app name")
parser.add_argument("-t","--as", default='ip', help="set args ip/host")
parser.add_argument("-o","--option", default='', help="set option default: ''")
parser.add_argument("-S","--session", default='default', help="set option default: default")




def main():
    args = parser.parse_args()
    
    if args.start:
        f = args.conf
        with open(f) as fp:
            w = json.loads(fp)
            assert  'server' in w
            assert  'server_port' in w
            assert  'password' in w
            assert  'method' in w
            run_server(w)

    if args.app:
        app = args.app[0]
        target = args.app[1]
        data = Task.build_json(app, session=args.session, **{getattr(args,'as'): target})
        

if __name__ == "__main__":
    main()
