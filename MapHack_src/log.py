import logging
from termcolor import colored



def L(*args):
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
    print(colored('[+]','green', attrs=['bold']),colored(' '.join(l), 'blue'))