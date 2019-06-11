import logging
from termcolor import colored
from MapHack_src.config import get_local_config


init_config = get_local_config()

def L(*args, log=False):
    l = []
    for i in args:
        if isinstance(i, dict):
            for k in i:
                if len(l) != 0:
                    l.append(colored('\b[+] ','green', attrs=['bold']) + "%s -> %s\n" % (colored(k,'magenta'), str(i[k])))
                else:
                    l.append("%s -> %s\n" % (colored(k,'magenta'), str(i[k])))
        elif isinstance(i, list):
            l.append("\n")
            l += i
        else:
            l.append(str(i))
    if log:
        print(colored('[+]','green', attrs=['bold']),colored(' '.join(l), 'blue'))
    else:
        logging.info(colored('\n[+]','green', attrs=['bold']) + " " + colored(' '.join(l), 'blue'))

