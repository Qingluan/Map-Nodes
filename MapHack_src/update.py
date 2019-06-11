import multiprocessing
import os, signal
import time
from MapHack_src.config import get_local_config
from MapHack_src.log import L
from subprocess import call
from MapHack_src.daemon import daemon_exec

config = get_local_config()

def update(port):
    for i in range(3):
        time.sleep(1)
        L('%d sec start update' % (3 -i))
    if os.path.exists("/tmp/Map-Nodes"):
        os.popen("cd /tmp/Map-Nodes && git pull origin master && pip3 install . -U ").read()
    else:

        os.popen("git clone https://github.com/Qingluan/Map-Nodes.git /tmp/Map-Nodes && cd /tmp/Map-Nodes && pip3 install . -U ").read()

    #os.kill(pid, signal.SIGKILL)
    res = None
    res = call("Seed-node -d stop", shell=True)
    L("kill process")
    L('restart node in 2 sec' )
    time.sleep(2)
    L('%d sec retry update' % 3 )
    time.sleep(3)
    res = call(config['base']['restart'].split())
    L(res)


def update_and_start(port): 
    o = multiprocessing.Process(target=update, args=(port, ))
    o.start()
    

