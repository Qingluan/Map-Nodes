import logging
from termcolor import colored
from MapHack_src.config import get_local_config
from base64 import b64decode


init_config = get_local_config()

def L(*args, log=False):
    l = []
    for i in args:
        if isinstance(i, dict):
            for k in i:
                if len(l) != 0:
                    l.append(colored('\b[+] ','green', attrs=['bold']) + "%s -> %s\n" % (colored(k,'magenta'), str(i[k])))
                else:
                    v = i[k]
                    if isinstance(v, str) and v.endswith('=='):
                        v = b64decode(v.encode()).decode()
                    else:
                        logging.debug(type(v))
                        v = str(v)
                    l.append("%s -> %s\n" % (colored(k,'magenta'), v))
        elif isinstance(i, list):
            l.append("\n")
            l += i
        else:
            l.append(str(i))
    if log:
        print(colored('[+]','green', attrs=['bold']),colored(' '.join(l), 'blue'))
    else:
        logging.info(colored('\n[+]','green', attrs=['bold']) + " " + colored(' '.join(l), 'blue'))

