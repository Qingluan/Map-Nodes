import multiprocessing
import os, signal
import time
from MapHack_src.config import get_local_config
from MapHack_src.log import L
from subprocess import call

config = get_local_config()

def update(pid, port):
    for i in range(3):
        time.sleep(1)
        L('%d sec start update' % (3 -i))
    if os.path.exists("/tmp/Map-Nodes"):
        os.popen("cd /tmp/Map-Nodes && git pull origin master && pip3 install . -U ").read()
    else:

        os.popen("git clone https://github.com/Qingluan/Map-Nodes.git /tmp/Map-Nodes && cd /tmp/Map-Nodes && pip3 install . -U ").read()

    os.kill(pid, signal.SIGKILL)
    try:
        #res = os.popen('lsof -t -i tcp:%d | xargs kill -9' % port).read()
        res = call("Seed-node" ,"--stop")
        L("kill process")
        L('restart node in 2 sec' )
        time.sleep(2)
        res = call(config['base']['restart'].split())
    except Exception as e:
        pass
    t = 5
    while 1:
        if t == 0:break
        if 'address already in use' in res:
            os.kill(pid, signal.SIGKILL)
            L('%d sec retry update' % 3 )
            time.sleep(3)
            try:
                res = os.popen(config['base']['restart']).read()
            except Exception as e:
                pass
        else:
            break
        t -= 1


    L(res)


def update_and_start(port): 
    o = multiprocessing.Process(target=update, args=(os.getpid(),port, ))
    o.start()
    

