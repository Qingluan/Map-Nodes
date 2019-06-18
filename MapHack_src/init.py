import os,json, re
import asyncssh
import asyncio
import logging
from getpass import getpass
from MapHack_src.log import L
from MapHack_src.config import get_local_config
from MapHack_src.selector import ip2geo
from sqlite3 import Connection

INIT_SCRIPT = """
#!/bin/bash
#install python
INS=apt-get
hash apt 2>/dev/null
if [ $? -eq 0 ];then
    echo "apt is existed install apt-lib"
    if [ -d /var/lib/dpkg/info ];then
        rm -rf /var/lib/dpkg/info;
        mkdir -p /var/lib/dpkg/info;
        apt install -f -y
    fi
    apt-get install -y libc6-dev gcc python3-pip
    apt-get install -y make build-essential libssl-dev zlib1g-dev libreadline-dev libsqlite3-dev wget curl llvm
else
    hash yum 2>/dev/null
    if [ $? -eq 0 ];then
        echo "yum is existed install yum-lib"
        yum -y install wget gcc make epel-release
        yum update -y
        yum -y install  net-tools python3-pip
        yum -y install zlib1g-dev bzip2-devel openssl-devel ncurses-devel sqlite-devel readline-devel tk-devel gdbm-devel db4-devel libpcap-devel xz-devel
        yum -y install python36
        INS=yum
    fi
fi


hash python3 2>/dev/null
if  [ $? -eq 0 ];then
  res=$(python3 -V 2>&1 | awk '{print $1}')
  version=$(python3 -V 2>&1 | awk '{print $2}')
  #echo "check command(python) available resutls are: $res"
  if [ "$res" == "Python" ];then
    if   [ "${version:0:3}" == "3.6" ];then
        echo "Command python3 could be used already."
             hash pip3 2>/dev/null;
             if [ $? -eq  0 ];then
                $INS install -y iputils-ping tree whois unzip python-pip
                exit 0
             else
                $INS install -y python3-pip python3-setuptools
                $INS install -y iputils-ping tree whois unzip python-pip
                exit 0
             fi
    fi
  fi
fi

echo "command python can't be used.start installing python3.6."
cd /tmp
    if [ -f /tmp/Python-3.6.1.tgz ];then
      rm /tmp/Python-3.6.1.tgz;
    fi
wget https://www.python.org/ftp/python/3.6.1/Python-3.6.1.tgz
tar -zxvf Python-3.6.1.tgz
cd Python-3.6.1
mkdir /usr/local/python3
./configure --prefix=/usr/local/python3
make
make install
if [ -f /usr/bin/python3 ];then
   rm /usr/bin/python3;
   rm /usr/bin/pip3;
fi

if [ -f /usr/bin/lsb_release ];then
  rm /usr/bin/lsb_release;
fi

ln -s /usr/local/python3/bin/python3 /usr/bin/python3
ln -s /usr/local/python3/bin/pip3 /usr/bin/pip3

echo 'export PATH="$PATH:/usr/local/python3/bin"' >> ~/.bashrc

$INS install -y iputils-ping tree whois unzip python-pip
"""

INSTALL_SCRIPT = """
INS=apt-get
hash apt 2>/dev/null
if [ $? -eq 0 ];then
    apt-get install -y python3-pip python3-setuptools
else
    yum install -y python3-pip python3*-devel
fi
cd /tmp/
if [ -d /tmp/Map-Nodes ];then
    rm -rf /tmp/Map-Nodes;
fi
git clone https://github.com/Qingluan/Map-Nodes.git
cd Map-Nodes && pip3 install . -U
if [ -f  $HOME/.maper.ini ];then
    rm $HOME/.maper.ini;
fi
if [ -f /var/run/hack.pid ];then
    kill -9 "$(cat /var/run/hack.pid)"
    rm /var/run/hack.pid;
fi
if [ -f /var/run/hack-updater.pid ];then
    kill -9 "$(cat /var/run/hack-updater.pid)";
    rm /var/run/hack-updater.pid;
fi
ps aux | grep Seed | awk '{print $2}' |xargs kill -9;
if [ -f $HOME/.mapper.json ];then
    rm $HOME/.mapper.json;
    rm $HOME/.maper.ini;
fi
"""

async def init_remote(host, password,port=22, user='root',conf=None):
    async with asyncssh.connect(host, port=int(port),username=user, password=password, client_keys=None,known_hosts=None ) as conn:
        result = await conn.run(INIT_SCRIPT)
        if result.exit_status == 0:
           result = await conn.run(INSTALL_SCRIPT)
           if result.exit_status != 0:
                L('error:',result.stderr)
        else:
            L('error:',result.stderr)

        async with conn.start_sftp_client() as sftp:
            await sftp.put(conf, '/root/.mapper.json')
            result = await conn.run("if [ -f /usr/local/python3/bin/Seed-node ];then /usr/local/python3/bin/Seed-node -c ~/.mapper.json -d start; /usr/local/python3/bin/Seed-node -c ~/.mapper.json -d start --updater; else Seed-node -c ~/.mapper.json -d start --updater ; Seed-node -c ~/.mapper.json -d start ; fi")
            if result.exit_status != 0:
                L(result.stderr)
        if result.exit_status == 0:
            return {'code':result.exit_status, "msg":"INIT ok", "ip":host}
        return {'code':result.exit_status, "msg":"error", "ip":host}

def init(host_str):
    user, host = host_str.split("@") if "@" in host_str else ["root", host_str]
    host,port = host.split(":") if ":" in host else [host, "22"]
    L(host, port, user)
    passwd = getpass()
    cport = input("port to config for this server [43000] :")
    password = input("password to connect [fuckgfw] :")
    method = input("method to encrypt [aes-256-cfb] :")

    cport = 43000 if not cport else int(cport)
    password = 'fuckgfw' if not password else password
    method = 'aes-256-cfb' if not method else method

    config = {
        'server':host,
        'server_port':cport,
        'password':password,
        'method':method
    }
    conf = get_local_config()
    root = os.path.expanduser(conf['client']['server_dir'])
    if not os.path.exists(root):
        os.mkdir(root)
    CLIENT_CONFIG = os.path.join(root, host)
    with open(CLIENT_CONFIG, 'w') as fp:
        json.dump(config, fp)

    loop = asyncio.get_event_loop()
    return loop.run_until_complete(init_remote(host,passwd, port=port,user=user, conf=CLIENT_CONFIG))

async def wait_err(host, pwd, port, user, conf):
    try:
        return await asyncio.wait_for(init_remote(host, pwd, port, user, conf=conf), timeout=50)    
    except asyncio.TimeoutError as e:
        return {'ip':host, 'msg':'Timeout', 'code': -1}


def init_from_db(db_file, country_or_ip):
    db = Connection(db_file)
    conf = get_local_config()
    loop = asyncio.get_event_loop()
    root = os.path.expanduser(conf['client']['server_dir'])
    if not os.path.exists(root):
        os.mkdir(root)
    if os.path.exists(db_file):
        servers = []
        try:
            if re.match(r'^\d{1,3}',country_or_ip):
                servers = db.execute("select host,passwd,port,user from  Host where host like '%{ip}%'".format(ip=country_or_ip)).fetchall()
                [L({'ip':i[0], 'country':ip2geo(i[0])}) for i in servers]
            elif country_or_ip == '.':
                servers = db.execute("select host,passwd,port,user from  Host").fetchall()
                [L({'ip':i[0], 'country':ip2geo(i[0])}) for i in servers]

            else:
                servers = []
                for i in db.execute("select host,passwd,port,user from  Host").fetchall():
                    if country_or_ip in ip2geo(i[0]).lower():
                        L({'ip':i[0], 'country':ip2geo(i[0])})
                        servers.append(i)
                
        except Exception as e:
            logging.error(e)
            servers =  []
        fs = []
        
        if input("sure to init ?:[y/other]").lower().strip() != 'y':
            return [{"msg":"exit "}]

        for server in servers:
            host,pwd,port, user = server
            config = {
                'server':host,
                'server_port':53000,
                'password': os.urandom(6).hex(),
                'method':'aes-256-cfb'
            }
            
            CLIENT_CONFIG = os.path.join(root, host)
            with open(CLIENT_CONFIG, 'w') as fp:
                json.dump(config, fp)
            L("--- to install ----")
            fs.append(wait_err(host,pwd, port, user, conf=CLIENT_CONFIG))
        return loop.run_until_complete(asyncio.gather(*fs))
    else:
        return []

