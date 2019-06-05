import logging
from termcolor import colored



def L(*args):
    l = []
    for i in args:
        if isinstance(i, dict):
            for k in i:
                l.append("%s -> %s" % (colored(k,'magenta'), str(i[k])))
        elif isinstance(i, list):
            l.append("\n")
            l += i
        else:
            l.append(i)
    print(colored('[+]','green', attrs=['bold']),colored(' '.join(l), 'blue'))