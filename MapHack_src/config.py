import os
import logging
import configparser

PATH = os.path.expanduser("~/.maper.ini")
if os.path.exists(PATH):
    pass
else:
    tmp = """
task_root = /tmp/tasks
level = INFO
restart = /usr/local/bin/Seed-node -d start -c /tmp/Map-Nodes/config.json                   

[app]
ping = apt-get install -y iputils-ping
nmap = apt-get install -y nmap
sqlmap = pip3 install sqlmap
dirsearch = git clone https://github.com/maurosoria/dirsearch.git /opt/dirsearch  && ln -s /opt/dirsearch/dirsearch.py /usr/local/bin/dirsearch                                            
masscan = apt-get -y install git gcc make libpcap-dev && cd /tmp/ &&  git clone https://github.com/robertdavidgraham/masscan  && cd masscan && make && make install                        
dirbpy = pip3 install dirbpy
whatweb = cd /opt/ && apt-get install -y gem ruby-devel && wget https://github.com/urbanadventurer/WhatWeb/archive/v0.4.9.zip -O /opt/whatweb.zip && cd /opt/ && unzip whatweb.zip ; ln -s /opt/WhatWeb-0.4.9/whatweb /usr/local/bin/whatweb                                             
dnsrecon = pip3 install netaddr dnspython lxml; git clone https://github.com/darkoperator/dnsrecon.git        /opt/dnsrecon && sed -ie 's/env python$/env python3/g' /opt/dnsrecon/dnsrecon.py && ln -s /opt/dnsrecon/dnsrecon.py /usr/local/bin/dnsrecon                                

[use]
nmap = nmap -sS -A {ip} {option}
dirsearch = dirsearch -u {ip} -e {option} --random-agents -s 2                               
sqlmap = sqlmap -t {ip} --dbs  {option}
ping = ping {ip} -c 5
masscan = masscan {ip}  -p22-10000  --banners --rate 1000                                    
dirbpy = dirbpy -o https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/common.txt -u {ip}
whatweb = whatweb  {option} {ip}
dnsrecon = dnsrecon {option} -d {ip}
"""
    with open(PATH, 'w') as fp:
        fp.write(tmp)

def get_local_config():

    config = configparser.ConfigParser()
    config.read(PATH)
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


