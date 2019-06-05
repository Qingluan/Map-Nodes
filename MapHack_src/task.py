import  sqlite3
import  asyncio
import  logging
import  datetime
import  os
from MapHack_src.config import  get_local_config, update

async def run_command(*args):
    # Create subprocess
    process = await asyncio.create_subprocess_exec(
        *args,
        # stdout must a pipe to be accessible as process.stdout
        stderr=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE)
    # Wait for the subprocess to finish
    stdout, stderr = await process.communicate()

    # Progress
    if process.returncode != 0:
        result = stderr.decode().strip()
        print('Failed:', args, '(pid = ' + str(process.pid) + ')')
    else:
        result = stdout.decode().strip()
    return process.returncode, result

async def check_cmd(command):
    code, res = await run_command("which", command)
    if not res:
        return False
    return  True

class Task:
    conf = get_local_config()
    def __init__(self, data):
        self._session = data["session"]
        self._data = data
        self._installer = 'apt-get update -y && apt-get install -y '
        root = os.path.join(self.conf['base']['task_root'], data['session'])
        if not os.path.exists(self.conf['base']['task_root']):
            os.mkdir(self.conf['base']['task_root'])
        if not os.path.exists(root):
            os.mkdir(root)
        self.root = root
    
    async def check(self):
        if  not (await check_cmd("apt-get")):
            self._installer = 'yum update -y && yum install -y'
        apps = list(self.conf['app'].keys())
        for app in apps:
            s = await check_cmd(app)
            if not s:
                lines = self.conf['app'][app].split("&&")
                res = [await run_command(line.split()) for line in lines]
                for code, res in res:
                    if code != 0:
                        logging.error("install %s failed" % app)
                        return  1, "install %s failed" % app
        return  0, 'check ok'

    async def Command(self, line):
        lines = [i.split() for i in  line.split("&&")]
        res = []
        code = 0
        for l in lines:
            c, r = await run_command(*l)
            res.append(r)
            code += c
        return  code,res
    
    async def run_app(self,app_name ,**kwargs):
        template = 'Not found in apps'
        try:
            template = self.conf['use'][app_name]
            cmd_str = template.format(**kwargs)
            D = datetime.datetime.now()
            log_file = os.path.join(self.root, "-".join([app_name, str(D.year),str(D.month), str(D.day)]) + ".log")
            code , res = await self.Command("nohup " + cmd_str + " > %s 2>&1" % log_file )
            return code, res
        except KeyError as e:
            return 1, template + str(e)
    
    
    async def get_app_log(self, app_name, date=None):
        if not date:
            date = datetime.datetime.now()
        log_file = os.path.join(self.root, "-".join([app_name, str(date.year),str(date.month), str(date.day)]) + ".log")
        with open(log_file,'rb') as fp:
            return  fp.read()
    
    async def kill_app(self, app_name):
        code, res = await self.Command("ps aux")
        if isinstance(res, bytes):
            res = res.decode()
        c = 0
        r = []
        for i in res.split("\n"):
            if "nohup" in i and  app_name in i:
                pid = i.split()[1]
                code, res = await self.Command("kill -9 " + pid)
                c += code
                r.append(res)
        return  c, r
    
    async def run(self):
        op = self._data['op']
        if op == 'run':
            app = self._data['app']
            kargs = self._data['kargs']
            code, res = self.run_app(app, **kargs)
        elif op == 'log':
            app = self._data['app']
            date = self._data('date')
            if not date:
                D = datetime.datetime.now()
            else:
                D = datetime.date(date.get['year'],date['mon'],date['day'])
            code,res = await self.get_app_log(app, date=D)        
        elif op == 'install':
            app = self._data['app']
            use = self._data['install']

            update('app',app,use['app'])
            update('use',app,use['use'])
        elif op == "test":
            session = self._data['session']
            code, res = await self.Command("ifconfig")
            res = session + "|" + res

        return  code, res
    
    @classmethod
    def build_json(cls, app, op='run', year=2019,mon=6,day=5, session=None,  **kargs):
        """
        @op :  run/log/install/test
        @kargs: 
            ['host', 'ip', 'option']
            like: ip="192.168.1.1"   for @app=nmap  
            like: host="https://test.ip/sdome.php?id=1" option='-D user --tables' for @app=sqlmap
        """
        if not session:
            session = os.urandom(8).hex()

        if op == 'run':
            D = {
                'op':op,
                'app':app,
                'session':session,
                'kargs':kargs
            }
        elif op == 'log':
            D = {
                'op':'log',
                'app':app,
                'session':session,
                'date':{
                    'year':year,
                    'mon':mon,
                    'day':day
                }
            }
        elif op == 'install':
            assert  'use' in kargs
            assert  'app' in kargs
            D = {
                'op':'install',
                'session':session,
                'app':app,
                'install':kargs
            }
        else:
            D = {
                'op':op,
                'session':session,
                'kargs':kargs
            }
            D.update(kargs)
        return  D

    @classmethod
    async def from_json(cls, json_data):
        if 'op' not in json_data:
            return 1,'must "op" in data'
        if 'session' not in json_data:
            return 2,'must session in data'
        # if 'app' not in json_data
        c = cls(json_data)
        code, res = await c.check()
        if code != 0:
            return  code, res
        return await c.run()

