import multiprocessing
import os, signal
import time
from MapHack_src.config import get_local_config
from MapHack_src.log import L
from subprocess import call
from MapHack_src.daemon import daemon_exec


config = get_local_config()
def update(port):
    config = get_local_config()
    for i in range(1):
        time.sleep(1)
        L('%d sec start update' % (1 -i))
    if os.path.exists("/tmp/Map-Nodes"):
        os.popen("cd /tmp/Map-Nodes && git pull origin master && pip3 install . -U ").read()
    else:

        os.popen("git clone https://github.com/Qingluan/Map-Nodes.git /tmp/Map-Nodes && cd /tmp/Map-Nodes && pip3 install . -U ").read()
    version = os.popen('cd /tmp/Map-Nodes/.git && cat FETCH_HEAD').read().split()[0]
    if version is None:
        version = time.asctime()
    L("new version:", version)

    #os.kill(pid, signal.SIGKILL)
    res = None
    res = call("Seed-node -d stop", shell=True)
    L("kill process")
    L('restart node in 0.5 sec' )
    time.sleep(0.5)
    restart_str = [os.path.expanduser(i) if i.startswith("~") else i for i in config['base']['restart'].split() ]
    res = call(restart_str)
    L(res)
    return version


def update_and_start(port): 
    o = multiprocessing.Process(target=update, args=(port, ))
    o.start()
    

