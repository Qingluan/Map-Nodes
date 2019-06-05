import os
import logging
import configparser

PATH = os.path.expanduser("~/.maper.ini")
if os.path.exists(PATH):
    pass
else:
    tmp = """
[base]
task_root = /tmp/tasks

[app]
ping = apt-get install -y iputils-ping
nmap = apt-get install -y nmap
sqlmap = pip3 install sqlmap
dirsearch = git clone https://github.com/maurosoria/dirsearch.git /opt/dirsearch  && ln -s /opt/dirsearch/dirsearch.py /usr/local/bin/dirsearch

[use]
nmap = nmap -sS -A {ip} {option}
dirsearch = dirsearch -h {host} -e {option}
sqlmap = sqlmap -t {host} --dbs  {option}
ping = ping {host} -c 5
"""
    with open(PATH, 'w') as fp:
        fp.write(tmp)

def get_local_config():

    config = configparser.ConfigParser()
    config.read(PATH)
    return  config

def update(sec, name, val):
    try:
        config = get_local_config()
        if sec not in config.sections():
            config.add_section(sec)
        config[sec][name] = val
        with open(PATH, 'w') as fp:
            config.write(fp)
    except  Exception as e:
        logging.error(e)



