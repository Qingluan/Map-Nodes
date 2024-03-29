import os
import logging
import configparser
import urllib.request as ur

PATH = os.path.expanduser("~/.maper.ini")
tmp = """
[base]
this = ~/.maper.ini
task_root = /tmp/tasks
level = INFO
restart = /usr/local/bin/Seed-node -d start -c /root/.mapper.json                   
FINISHED_LOG_FILE = /tmp/finished_pids
log_file = 

[client]
server_dir = ~/.server_dir
server_ini = ~/.server_inis
server_session = ~/.server_session
server_log = ~/.server_logs

[app]
whois = apt-get install -y whois
tree = apt-get install -y tree
ping = apt-get install -y iputils-ping
nmap = apt-get install -y nmap
sqlmap = pip3 install sqlmap
dirsearch = git clone https://github.com/maurosoria/dirsearch.git /opt/dirsearch  && ln -s /opt/dirsearch/dirsearch.py /usr/local/bin/dirsearch                                            
masscan = apt-get -y install git gcc make libpcap-dev* && cd /tmp/ &&  git clone https://github.com/robertdavidgraham/masscan  && cd masscan && make && make install                        
dirbpy = pip3 install dirbpy
whatweb = rm /usr/local/bin/whatweb ; cd /opt/ && apt-get install -y unzip gem ruby-dev* && wget https://github.com/urbanadventurer/WhatWeb/archive/v0.4.9.zip -O /opt/whatweb.zip && cd /opt/ && unzip whatweb.zip && ln -s /opt/WhatWeb-0.4.9/whatweb /usr/local/bin/whatweb                                             
dnsrecon = apt-get install -y python-pip && pip install netaddr lxml dnspython ;  git clone https://github.com/darkoperator/dnsrecon.git /opt/dnsrecon && ln -s /opt/dnsrecon/dnsrecon.py /usr/local/bin/dnsrecon                                

[use]
tree = tree {ip} {option}
nmap = nmap -sS -A {ip} {option}
dirsearch = dirsearch -u {http} -e {option} --random-agents -s 2                               
sqlmap = sqlmap -t {http} --dbs  {option}
ping = ping {ip} -c 5
masscan = masscan {ip}  -p22-10000  --banners --rate 1000                                    
dirbpy = dirbpy -o https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/common.txt -u {http}
whatweb = whatweb  {option} {ip}
dnsrecon = dnsrecon {option} -d {ip}
whois = whois {ip} {option}
"""

if os.path.exists(PATH):
    pass
else:
    with open(PATH, 'w') as fp:
        fp.write(tmp)

def update_ini_from_git():
    url = 'https://raw.githubusercontent.com/Qingluan/Map-Nodes/master/template.ini'
    try:
        response = urllib.request.urlopen(url)
        data = response.read()
        if not data:
            PATH = os.path.expanduser("~/.maper.ini")
            with open(PATH, 'w') as fp:
                fp.write(data.decode())
                return True
    except Exception as e:
        return False

def get_local_config():

    config = configparser.ConfigParser()
    if not os.path.exists(PATH):
        logging.error("no ini file")
        with open(PATH, 'w') as fp:
            fp.write(tmp)
    config.read(PATH)
    task_root = config['base']['task_root']
    if not os.path.exists(task_root):
        os.mkdir(task_root)
    if not os.path.exists(os.path.join(config['base']['task_root'], 'config')):
        os.mkdir(os.path.join(config['base']['task_root'],'config'))
    for k in config['client'].keys():
        p = os.path.expanduser(config['client'][k])
        try:
            if not os.path.exists(p):
                os.mkdir(p)
        except Exception as e:
            logging.error(e)
    if config['base']['log_file']:
        logging.basicConfig(level=getattr(logging,config['base']['level']), filename=config['base']['log_file'])
    else:
        logging.basicConfig(level=getattr(logging,config['base']['level']))
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



def test_ini(f):
    config = configparser.ConfigParser()
    config.read(f)
    a = config.sections()
    assert 'app' in a
    assert 'use' in a
    assert 'base' in a
    config['base']['task_root']
    config['app']['ping']
    config['use']['ping']
    config['base']['level']

    
    config2 = configparser.ConfigParser()
    config2.read(PATH)
    for sec in ['base','app', 'use']:
        for k in config[sec].keys():
            config2[sec][k] = config[sec][k]
    
    with open(PATH, 'w') as fp:
        config2.write(fp)

def get_ini():
    with open(PATH, 'r') as fp:
        return fp.read()


local_conf = get_local_config()
