from termcolor import colored

def L(*args):
    print(colored('[+]','green', attrs=['bold']),colored(' '.join([str(i) for i in args]), 'red'))