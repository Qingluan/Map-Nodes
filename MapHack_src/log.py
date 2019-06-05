import logging
from termcolor import colored

logging.basicConfig(level=logging.INFO)

def L(*args):
    print(colored('[+]','green', attrs=['bold']),colored(' '.join([str(i) for i in args]), 'red'))