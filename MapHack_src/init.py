import os,json
import asyncssh
import asyncio
from getpass import getpass
from MapHack_src.log import L
from MapHack_src.config import get_local_config


INIT_SCRIPT = """
#!/bin/bash
#install python
INS=apt
hash apt 2>/dev/null
if [ $? -eq 0 ];then
    echo "apt is existed install apt-lib"
    apt-get install -y libc6-dev gcc
    apt-get install -y make build-essential libssl-dev zlib1g-dev libreadline-dev libsqlite3-dev wget curl llvm
else
    hash yum 2>/dev/null
    if [ $? -eq 0 ];then
        echo "yum is existed install yum-lib"
        yum -y install wget gcc make epel-release
        yum update -y
        yum -y install  net-tools
        yum -y install zlib1g-dev bzip2-devel openssl-devel ncurses-devel sqlite-devel readline-devel tk-devel gdbm-devel db4-devel libpcap-devel xz-devel
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
                exit 0
             else
                $INS install -y python3-pip python3-setuptools
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

"""

INSTALL_SCRIPT = """
cd /tmp/
git clone https://github.com/Qingluan/Map-Nodes.git
cd Map-Nodes && pip3 install . -U
"""

async def init_remote(host, password,port=22, user='root',conf=None):
    async with asyncssh.connect(host, port=int(port),username=user, password=password, client_keys=None,known_hosts=None ) as conn:
        result = await conn.run(INIT_SCRIPT)
        if result.exit_status == 0:
            result = await conn.run(INSTALL_SCRIPT)
            async with conn.start_sftp_client() as sftp:
                await sftp.put(conf, '/root/.mapper.json')
                result = await conn.run("Seed-node -c ~/.mapper.json -d start; Seed-node -c ~/.mapper.json -d start --updater")

        if result.exit_status == 0:
            return "INIT ok"
        return "failed"

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
