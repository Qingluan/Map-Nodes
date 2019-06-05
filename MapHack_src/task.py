import  sqlite3
import  asyncio
import  logging
import  datetime
import  os
from base64 import  b64encode, b64decode
from concurrent.futures.thread import  ThreadPoolExecutor
from MapHack_src.config import  get_local_config, update, test_ini

async def run_command(*args, stdout=None):
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

async def run_shell(shell, stdout=None, background=False):
    # Create subprocess
    
    if background:
        if stdout:
            stderr = stdout + ".err"
            shell = shell + " >" + stdout + " 2> " + stderr

        shell = "nohup " + shell + " &"
    process = await asyncio.create_subprocess_exec(
        'bash','-c',shell,
        # stdout must a pipe to be accessible as process.stdout
        stderr=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE)
    # Wait for the subprocess to finish
    stdout, stderr = await process.communicate()

    # Progress
    if process.returncode != 0:
        result = stderr.decode().strip()
        print('Failed:', shell, '(pid = ' + str(process.pid) + ')')
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
    Pocket = ThreadPoolExecutor(max_workers=12)

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
    
    @classmethod
    async def Check(cls):
        c = cls({"session": "test", "app":"ping", "op":'run'})
        return await c.check()

    async def check(self):
        if  not (await check_cmd("apt-get")):
            self._installer = 'yum update -y && yum install -y'
        apps = list(self.conf['app'].keys())
        for app in apps:
            s = await check_cmd(app)
            if not s:
                # lines = self.conf['app'][app].split("&&")
                # res = [await run_command(*line.split()) for line in lines]
                code, res = await run_shell(self.__class__.conf['app'][app])
                # for code, res in res:
                if code != 0:
                    logging.error("install %s failed" % app)
                    return  1, "install %s failed" % app
        return  0, 'check ok'

    async def Command(self, line, stdout=None):
        lines = [i.split() for i in  line.split("&&")]
        res = []
        code = 0
        for l in lines:
            c, r = await run_command(*l, stdout=stdout)
            res.append(r)
            code += c
        return  code,res
    
    async def run_app(self,app_name, background=False, **kwargs):
        template = 'Not found in apps'
        try:
            template = self.conf['use'][app_name]
            cmd_str = template.format(**kwargs)
            D = datetime.datetime.now()
            log_file = os.path.join(self.root, "-".join([app_name, str(D.year),str(D.month), str(D.day)]) + ".log")
            if not background:
                try:
                    code , res = await asyncio.wait_for(run_shell(cmd_str, stdout=log_file), 12)
                except asyncio.TimeoutError:
                    code = 2
                    res1 =  "timeout ... try : use background... but failed"
                    code , res = await run_shell(cmd_str, stdout=log_file, background=True)
                    if code != 0:
                        return code, res1
            else:
                code , res = await run_shell(cmd_str, stdout=log_file, background=True)
            return code, res
        except KeyError as e:
            return 1, template + str(e)
        
    
    
    async def get_app_log(self, app_name, date=None):
        if not date:
            date = datetime.datetime.now()
        log_file = os.path.join(self.root, "-".join([app_name, str(date.year),str(date.month), str(date.day)]) + ".log")
        err_log_file = log_file + ".err"
        log = {}
        if os.path.exists(log_file):
            with open(log_file,'rb') as fp:
                log['log'] = b64encode(fp.read()).decode()
        if os.path.exists(err_log_file):
            with open(err_log_file,'rb') as fp:
                log['err_log'] = b64encode(fp.read()).decode()
        if not log:
            return  1, 'no any log for "%s" ' % app_name
        return 0,log
    
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
            background = self._data.get("background", False)
            code, res = await self.run_app(app,background=background,**kargs)
        elif op == 'log':
            app = self._data['app']
            date = self._data.get('date')
            if not date:
                date = datetime.datetime.now()
            
            D = datetime.date(date['year'],date['mon'],date['day'])
            code,res = await self.get_app_log(app, date=D)        
        elif op == 'install':
            app = self._data['app']
            use = self._data['install']
            update('app',app,use['app'])
            update('use',app,use['use'])
        elif op == 'sync-ini':
            code , res = await asyncio.get_event_loop().run_in_executor(self.__class__.Pocket, self.test_ini_file, self._data['content'])
            if code == 0:
                code2, res2 = await self.check()
                code += code2
                if isinstance(res2, list):
                    res2 = '\n'.join(res2)
                res = res2 + '\n' + res
        elif op == 'update':
            code, res = await asyncio.get_event_loop().run_in_executor(self.__class__.Pocket,self.check)
        elif op == "test":
            session = self._data['session']
            code, res = await self.Command("ifconfig")
            res = session + "|" + '\n'.join(res)

        return  code, res
    
    def test_ini_file(self, content):
        f = "/tmp/%s" % os.urandom(8).hex() +".ini"
        with open(f, 'w' ) as fp:
            fp.write(content)
        try:
            test_ini(f)
            self.__class__.conf = get_local_config()
            return 0,"update ini and reload ini file."
        except  Exception as e:
            os.remove(f)
            return  1,str(e)
        
    
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

