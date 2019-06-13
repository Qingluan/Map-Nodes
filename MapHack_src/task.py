import  sqlite3, json, time
import  asyncio
import  logging
import  datetime
import  os, signal
from base64 import  b64encode, b64decode
from concurrent.futures.thread import  ThreadPoolExecutor
from MapHack_src.config import  get_local_config, update, test_ini, get_ini
from MapHack_src.log import L
from MapHack_src.update import update_and_start


class TaskData:
    Datas = {}
    RDatas = {}

    @classmethod
    def get(cls, pid):
        if not cls.Datas:
            cls.load()

        if pid in cls.Datas:
            return cls.Datas.get(pid)
        elif pid in cls.RDatas:
            pid = os.path.basename(pid) if '/' in pid else pid
            return cls.RDatas[pid]

    @classmethod
    def finish(cls, pid):
        if pid in cls.Datas:
            log = cls.get(pid)
            del cls.Datas[pid] 
            del cls.RDatas[log]
        elif pid in cls.RDatas:
            log = cls.get(pid)
            del cls.RDatas[pid]
            del cls.Datas[log]


    @classmethod
    def set(cls, pid, log_file):
        log_file = os.path.basename(log_file) if '/' in log_file else log_file
        cls.Datas[pid] = log_file
        cls.RDatas[log_file] = pid

    @classmethod
    def logs(cls):
        return list(cls.RDatas.keys())

    @classmethod
    def pids(cls):
        return list(cls.Datas.keys())
 
    @classmethod
    def running(cls, pid):
        if pid in cls.RDatas:
            pid = os.path.basename(pid) if '/' in pid else pid
            pid = cls.get(pid)
        
        if pid and isinstance(pid, int):
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return False
            else:
                return True
        return False

    @classmethod
    def save(cls, a,b):
        L("save task info ")
        with open("/tmp/task_info.json", 'w') as fp:
            json.dump({'p':cls.Datas, 'l':cls.RDatas}, fp)
    
    @classmethod
    def load(cls):
        if os.path.exists("/tmp/task_info.json"):
            L("load task info ")
            with open("/tmp/task_info.json") as fp:
                d = json.load(fp)
                cls.Datas.update(d['p'])
                cls.RDatas.update(d['l'])
            os.remove("/tmp/task_info.json")

#signal.signal(signal.SIGTERM, TaskData.save)

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
        # print('Failed:', args, '(pid = ' + str(process.pid) + ')')
    else:
        result = stdout.decode().strip()
    return process.returncode, result

async def run_shell(shell, stdout=None, background=False):
    # Create subprocess
    
    log_file = None
    if background:
        if stdout:
            stderr = stdout + ".err"
            shell = shell + " >" + stdout + " 2> " + stderr

        shell = "nohup " + shell + " &"
        result = 'run in background: %s ' % stdout
        log_file = stdout
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
        L("failed:", result)
    else:
        if log_file and background:
            pid = process.pid
            TaskData.set(pid, log_file)
        result = stdout.decode().strip()
    return process.returncode, result

async def check_cmd(command):
    code, res = await run_command("which", command)
    if not res or code != 0:
        return False
    return  True

class Task:

    conf = get_local_config()
    Pocket = ThreadPoolExecutor(max_workers=12)

    def __init__(self, data, pconf=None, sender=None):
        self._session = data["session"]
        self._data = data
        self.Sender = sender
        self._installer = 'apt-get update -y && apt-get install -y '
        self.root_config = os.path.join(self.conf['base']['task_root'],'config')
        if not os.path.exists(self.root_config):
            os.mkdir(self.root_config)
        root = os.path.join(self.conf['base']['task_root'], data['session'])
        if not os.path.exists(self.conf['base']['task_root']):
            os.mkdir(self.conf['base']['task_root'])
        if not os.path.exists(root):
            os.mkdir(root)
        self.root = root
        self._pconf = pconf
    
    @classmethod
    async def Check(cls):
        c = cls({"session": "test", "app":"ping", "op":'run'})
        return await c.check()

    async def check(self):
        res = 'use apt '
        if  not (await check_cmd("apt-get")):
            self._installer = 'yum'
            L("may be centos , use : yum")
            res = "may be centos, use yum"
        apps = list(self.conf['app'].keys())
        for app in apps:
            s = await check_cmd(app)
            if not s:
                # lines = self.conf['app'][app].split("&&")
                # res = [await run_command(*line.split()) for line in lines]
                install_str = self.__class__.conf['app'][app]
                if self._installer == 'yum':
                    install_str = install_str.replace("apt-get", self._installer)

                D = datetime.datetime.now()
                log_file = os.path.join(self.root_config, "-".join([app, str(D.year),str(D.month), str(D.day)]) + ".log")
                code, res2 = await run_shell(install_str, background=True, stdout=log_file)
                res += res2
                # for code, res in res:
                if code != 0:
                    logging.error("install %s failed" % app)
                    if app in os.listdir('/tmp/') and 'git' in install_str:
                        await run_shell("rm -rf /tmp/" + app.strip())
                    return  1, res + "\ninstall %s failed || %s" % (app, res)
        return  0, res + '\ncheck ok'

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
                        return code, res
            else:
                L("logfile : " , log_file)
                code , res = await run_shell(cmd_str, stdout=log_file, background=True)
                res = cmd_str
            return code, res
        except KeyError as e:
            return 1, template + str(e)

    def load_tasks(self):
        for root, ds, fs in os.walk(self.root):
            for f in fs:
                if f.endswith('.log'):
                    yield f
        
    async def check_tasks(self):
        ks = list(self.load_tasks())
        result = {}
        for log in ks:
            f = TaskData.running(log)
            result[log] = f
        return 0,result
    
    async def check_info(self):
        session = os.listdir(self.conf['base']['task_root'])
        apps = list(self.conf['use'].keys())
        return 0, {'session':session, 'app': apps}
    
    async def get_app_log(self, app_name, date=None,pid=None, line=50):
        if not date:
            date = datetime.datetime.now()
        if not isinstance(date, str):
            log_file = os.path.join(self.root, "-".join([app_name, str(date.year),str(date.month), str(date.day)]) + ".log")
        else:
            log_file = os.path.join(self.root, app_name + "-%s" % date + ".log")

        if pid and pid in TaskData.Datas:
            log_file = TaskData.get(pid)

        err_log_file = log_file + ".err"
        log = {}
        running = TaskData.running(log_file)
        running_if_str = '\n[Running]' if running else '\n[Stop]'
        if not running:
            TaskData.finish(TaskData.get(log_file))

        if os.path.exists(log_file):
            #with open(log_file,'rb') as fp:
            #    log['log'] = b64encode(fp.read()).decode()
            log['log'] = b64encode((await run_shell("tail -n %d %s " % (line,log_file) ))[1].encode() + running_if_str.encode() ).decode('utf-8','ignore')
        if os.path.exists(err_log_file):
            #with open(err_log_file,'rb') as fp:
            #    log['err_log'] = b64encode(fp.read()).decode()
            log['err_log'] = b64encode((await run_shell("tail -n %d %s " % (line,err_log_file) ))[1].encode()).decode('utf-8','ignore')
        if not log:
            return  1, 'no any log for "%s" in %s %s' % (app_name, log_file, running_if_str) 
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
        L(self._data)
        if op == 'run':
            app = self._data['app']
            kargs = self._data['kargs']
            code, res = await self.run_app(app,**kargs)
        elif op == 'log':
            app = self._data['app']
            date = self._data.get('date')
            line = int(self._data.get('line',50))
            if not date:
                date = datetime.datetime.now()

            if isinstance(date, dict):
                D = datetime.date(date['year'],date['mon'],date['day'])
            else:
                D = date
            code,res = await self.get_app_log(app,line=line, date=D)        
        elif op == 'install':
            app = self._data['app']
            try:
                install_str = self.conf['app'][app]
                D = datetime.datetime.now()
                log_file = os.path.join(self.root_config, "-".join([app, str(D.year),str(D.month), str(D.day)]) + ".log")
                code, res = await run_shell(install_str, background=True, stdout=log_file)
            except Exception as e:
                code = 1
                res = str(e)
        elif op == 'get-ini':
            content = get_ini()
            code = 0
            res = content
        elif op == 'sync-ini':
            code , res = await asyncio.get_event_loop().run_in_executor(self.__class__.Pocket, self.test_ini_file, self._data['content'])
            if code == 0:
                code2, res2 = await self.check()
                code += code2
                if isinstance(res2, list):
                    res2 = '\n'.join(res2)
                res = res2 + '\n' + res
        elif op == 'update':
            code, res = await self.check()
        elif op == 'check':
            code, res = await self.check_tasks()
        elif op == 'info':
            code, res = await self.check_info()
        elif op == 'list':
            session = self._data['session']
            app = self._data.get('app','')
            log_dir = self.root
            use_app = {k: self.conf['use'][k] for k in self.conf['use'].keys()}
            if app:
                use_app['log_list'] = {}
                for log in os.listdir(log_dir):
                    if log.startswith(app):
                        use_app['log_list'][app] = log

            return 0, use_app

        elif op == "test":
            session = self._data['session']
            code, res = await self.Command("ifconfig")
            res = session + "|" + '\n'.join(res)
        
        elif op == 'upgrade-local':
            TaskData.save(None,None)
            update_and_start(self._pconf['server_port'])
            data = Task.build_json('', op="upgrade-local-fi", session=self._session)
            with open(os.path.expanduser("~/.mapper.json")) as fp:
                w = json.load(fp)
            time.sleep(12)
            loop = asyncio.get_event_loop()
            err_try = 0
            res = ''
            L(w)
            while 1:
                try:
                    res = await self.Sender(w, data,loop)
                    break
                except OSError as e:
                    if err_try > 3:
                        res = 'try bad' + str(e)
                        L("try restart updater: %d: %s" % (err_try, res))
                        break
                    err_try += 1
                    time.sleep(5)
            code = 0
        elif op == 'upgrade-local-fi':
            code, res = await run_shell("Seed-node -d stop --updater && Seed-node -d start --updater -c ~/.mapper.json")
        elif op == 'upgrade':
            data = Task.build_json('', op="upgrade-local", session=self._session)
            w = self._pconf
            if 'mark' not in self._pconf:
                w['server'] = 'localhost'
                w['server_port'] = str(int(w['server_port']) + 1)
                w['mark'] = True
            loop = asyncio.get_event_loop()
            res = await self.Sender(w, data,loop)
            code, res = 0, "ready update"

        elif op == 'exec':
            session = self._data['session']
            app = self._data['app']
            code, res = await run_shell(app)


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
    def build_json(cls, app, op='run', year=None,mon=None,day=None, session=None,  **kargs):
        """
        @op :  run/log/install/test
        @kargs: 
            ['host', 'ip', 'option']
            like: ip="192.168.1.1"   for @app=nmap  
            like: host="https://test.ip/sdome.php?id=1" option='-D user --tables' for @app=sqlmap
        """
        if not year:
            dd = datetime.datetime.now()
            year = dd.year
            mon = dd.month
            day = dd.day
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
            d = kargs.get('date')
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
            D.update(kargs)
            if d:
                D['date'] = d
        elif op == 'install':
            D = {
                'op':'install',
                'session':session,
                'app':app,
                'install':kargs
            }
        else:
            D = {
                'app':app,
                'op':op,
                'session':session,
                'kargs':kargs
            }
            D.update(kargs)
        return  D

    @classmethod
    async def from_json(cls, json_data, conf=None, sender=None):
        if 'op' not in json_data:
            return 1,'must "op" in data'
        if 'session' not in json_data:
            return 2,'must session in data'
        # if 'app' not in json_data
        c = cls(json_data, pconf=conf, sender=sender)
        # code, res = await c.check()
        # if code != 0:
            # return  code, res
        code, res = await c.run()
        return  code, res

