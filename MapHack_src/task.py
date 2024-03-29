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
HELP = """
optional arguments:
  run -a [app target] -o [option]          run app [default]
  install  -a [app] -s [session]           install app

  ps -s [session]                          show task status in session
  tree                                     show all log tree
  log -a [app] -s [session]                show log content in session and app
  cl -s [session]                          clear session log and session task record
  cla                                      clear all session's log and task records
  kill -a [app] -s [session]               kill task in session with running app , and get log

  info                                     get info of server
  sys-log                                  get server's log

  upgrade                                  upgrade from git
  test                                     test if config file is ok and get server's ifconfig
  ls                                       list all app in config
  
  update                                   to install all app in list.
  clean                                    clear all installed app .
"""
FINISHED_LOG_FILE = '/tmp/finished_pids'
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
        log_file = log_file
        cls.Datas[pid] = log_file
        cls.RDatas[log_file] = pid

    @classmethod
    def logs(cls):
        return list(cls.RDatas.keys())

    @classmethod
    def clear_session(cls, session):
        ks = list(cls.RDatas.keys())
        for log in ks:
            if log.startswith(session):
                cls.finish(log)

    @classmethod
    def pids(cls):
        return list(cls.Datas.keys())
 
    @classmethod
    def running(cls, pid, session_root='/tmp/tasks/config'):
        
        if isinstance(pid, str) and pid.endswith(".log"):
            pid_f = os.path.join(session_root, pid[:-4] + ".pid" )
            if os.path.exists(pid_f):
                with open(pid_f) as fp:
                    
                    pid = int(fp.read().strip())
                    L({pid_f: pid})
        if pid in cls.RDatas:
            pid = cls.get(pid)
            L("test:runing:", pid)
        
        if pid and isinstance(pid, int):
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                L({pid: False}, 'not run')
                return False
            else:
                L({pid: True}, 'run')
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

async def run_shell(shell, stdout=None, background=False,use_script=False, finished_log_file=FINISHED_LOG_FILE):
    # Create subprocess
    # assert stdout is not None
    log_file = None
    pid_file = None
    if ';' in shell or '&&' in shell:
        use_script = True
    if use_script:
        exe_script = "/tmp/script.sh"
        if os.path.exists(exe_script):
            exe_script = '/tmp/%s.sh' % (os.urandom(6).hex())

        with open(exe_script, 'w') as fp:

            fp.write("#!/bin/bash\n" + shell)
            if stdout:
                fp.write("\n echo %s >>  %s ; rm %s" %(stdout, finished_log_file, exe_script))

        shell = "bash " + exe_script

    if background:
        if stdout:
            stderr = stdout + ".err"
            pid_file = stdout[:-4] + ".pid"
            # shell  += '; echo %s >> %s ' % (pid_file, finished_log_file)
            shell = shell + " >" + stdout + " 2> " + stderr
        shell = "nohup " + shell + " &"
        result = 'run in background: %s ' % stdout
        log_file = stdout
    L({'run in backgroun':shell})

    process = await asyncio.create_subprocess_exec(
        'bash','-c',shell,
        # stdout must a pipe to be accessible as process.stdout
        stderr=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE)

    stdout, stderr = await process.communicate()
    pid = process.pid
    if background:
        pid += 1

    # Progress
    if process.returncode != 0:
        if pid_file:
            with open(pid_file, 'w') as fp:
                fp.write(str(process.pid))
        result = stderr.decode().strip()
        L("failed:", result)
    else:

        if log_file and background:
            TaskData.set(pid, log_file)
            result = stderr.decode().strip()
            if pid_file:
                with open(pid_file, 'w') as fp:
                    fp.write(str(process.pid + 1))
        result = stdout.decode().strip()
        if not result:
            if pid:
                result = str(pid) + ":" + str(log_file)
    # L(TaskData.RDatas)
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
        if self._installer != 'yum':
            INSTALL = 'ps aux | grep "(apt-get|dpkg)" | grep -v "grep" | awk \'{print $2 }\' | xargs kill -9  ; dpkg --configure -a ;\nif [ -f /var/lib/dpkg/lock ];then rm /var/lib/dpkg/lock;fi \n if [ -f /var/cache/apt/archives/lock ];then rm /var/cache/apt/archives/lock ;fi ; apt-get update -y && apt --fix-broken install -y ; apt-get install -f -y ;  apt remove -y ; mv /var/lib/dpkg/info/polar-bookshelf.* /tmp \n'
        else:
            INSTALL = ''
        for app in apps:
            s = await check_cmd(app)
            if not s:
                # lines = self.conf['app'][app].split("&&")
                # res = [await run_command(*line.split()) for line in lines]
                install_str = self.__class__.conf['app'][app]
                if self._installer == 'yum':
                    install_str = install_str.replace("apt-get", self._installer)

                # fs.append(run_f)
                INSTALL += install_str + ";"
                res += install_str + ";\n"
        D = datetime.datetime.now()
        log_file = os.path.join(self.root_config, "-".join(["install", str(D.year),str(D.month), str(D.day)]) + ".log")
        code,res2 = await run_shell(INSTALL, background=True, stdout=log_file, use_script=True)
        return  0, res + '\n---------------------\n' + res2

    async def uninstall(self):
        apps = list(self.conf['app'].keys())
        CLEAR = ''
        for app in apps:
            
            clear_str = ' apt remove -y %s ; pip3 uninstall -y %s ; pip uninstall -y %s ;' % (app, app, app)
            install_str = self.__class__.conf['app'][app]
            if 'ln -s' in install_str:
                clear_str += '\n rm /usr/local/bin/%s;' % app
            if os.path.exists("/opt/%s" % app):
                clear_str += '\n rm -rf /opt/%s ;' % app 
            CLEAR += clear_str  + "\n"

        if os.path.exists(os.path.expanduser("~/.maper.ini")):
            CLEAR += '\n rm %s' % os.path.expanduser("~/.maper.ini")

        D = datetime.datetime.now()
        log_file = os.path.join(self.root_config, "-".join(["uninstall", str(D.year),str(D.month), str(D.day)]) + ".log")
        code,res = await run_shell(CLEAR, background=True, stdout=log_file, use_script=True)
        if not res:
            res = CLEAR
        return code, res

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
            if '{http}' in template:
                if 'ip' in kwargs:
                    v = kwargs['ip']
                    del kwargs['ip']
                elif 'http' in kwargs:
                    v = kwargs['http']
                if not v.startswith('http'):
                    v = 'http://' + v
                    
                kwargs['http'] = v
            else:
                v = kwargs['ip']
                if 'http://' in v:
                    v = v.split("http://")[1]
                elif 'https://' in v:
                    v = v.split('https://')[1]
                if 'http' in kwargs:
                    del kwargs['http']
                kwargs['ip'] = v

            cmd_str = template.format(**kwargs)
            D = datetime.datetime.now()
            log_file = os.path.join(self.root, "-".join([app_name, str(D.year),str(D.month), str(D.day)]) + ".log")
            if not background:
                try:
                    code , res = await asyncio.wait_for(run_shell(cmd_str, stdout=log_file), 12)
                    with open(log_file, 'w') as fp:fp.write(res)
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
        # finished_logs = ''
        # if os.path.exists(FINISHED_LOG_FILE):
            
        #     with open(FINISHED_LOG_FILE) as fp:
        #         finished_logs = fp.read()
        result = {}
        for log in ks:
            f = TaskData.running(log, session_root=self.root)
            result[log] = f
        # result['finished'] = finished_logs
        return 0,result
    
    async def check_info(self):
        if 'version' not in list(self.conf['base'].keys()):
            version = 'X'
        else:
            version = self.conf['base']['version']
        R = self.conf['base']['task_root']
        sessions = os.listdir(R)
        logs = {}
        for session in sessions:
            sess_root = os.path.join(R, session)
            for log in os.listdir(sess_root):
                logs[session+"/" + log] = TaskData.running(log, session_root=sess_root)

        apps = list(self.conf['use'].keys())

        return 0, {'session':sessions, 'app': apps, 'version':version, 'ps':logs}
    
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
        running = TaskData.running(log_file, session_root=self.root)
        running_if_str = '\n[Running]' if running else '\n[Stop]'
        # if not running:
        #     TaskData.finish(TaskData.get(log_file))

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
    
    async def get_sys_log(self):
        log = {}
        code = 0
        line = 100
        if os.path.exists("/var/log/hack.log"):
            log_file = "/var/log/hack.log"
            log['log'] = b64encode((await run_shell("tail -n %d %s " % (line,log_file) ))[1].encode())\
                        .decode('utf-8','ignore')
        else:
            code += 1
        if os.path.exists("/var/log/hack-updater.log"):
            err_log = "/var/log/hack-updater.log"        
            log['err_log'] = b64encode((await run_shell("tail -n %d %s " % (line,err_log) ))[1].encode())\
                        .decode('utf-8','ignore')
        else:
            code += 10
        # L(log)
        return code, log
    
    async def clear_session(self):
        if os.path.exists(self.root):
            if ' ' in self.root or '..' in self.root or '~' in self.root:
                code = 1
                res = 'warring do not do this : rm -rf %s' % self.root
                return code , res
            if not self.root.startswith('/tmp'):
                code = 1
                res = 'warring do not do this : rm -rf %s' % self.root
                return code , res
            code, res = await run_shell('rm -rf %s' % self.root, background=False)
        if self.root.endswith('config'):
            os.mkdir(self.root)
        if code == 0:
            res = 'clear session : %s ' % self.root
            TaskData.clear_session(self.root)
        return code, res

    async def clear_all(self):
        TaskData.RDatas = {}
        TaskData.Datas = {}
        root = self.conf['base']['task_root']
        code, res = await run_shell('rm -rf %s ' % root, background=False)
        if code == 0:
            code, res = await run_shell('mkdir %s ' % root, background=False)
            code, res = await run_shell('mkdir %s/config ' % root, background=False)
        if code == 0:
            res = 'clear all session and log'
        return code, res

    async def clear_task(self, app, session, time):
        assert isinstance(time, str)
        log_file = '-'.join([app , time]) + ".log"
        pid_file = '-'.join([app , time]) + ".pid"
        log_file = os.path.join(self.root, log_file)
        pid_file = os.path.join(self.root, pid_file)
        err_log = log_file + ".err"
        res = {}
        code = 0
        if os.path.exists(pid_file):
            try:
                pid = int(open(pid_file).read())
                os.kill(pid, signal.SIGTERM)
                res['shutdown'] = True
            except Exception as e:
                res['err'] = str(e)
                res['shutdown'] = False
                code = 1
        if os.path.exists(log_file):
            res['log'] = b64encode((await run_shell("cat %s " % (log_file) ))[1].encode())\
                .decode('utf-8','ignore')
        else:
            code += 10
        if os.path.exists(err_log):
            res['err_log'] = b64encode((await run_shell("cat %s " % (err_log) ))[1].encode())\
                .decode('utf-8','ignore')
        else:
            code += 100
        return code, res

    async def get_sessions(self):
        r = self.conf['base']['task_root']
        if r:
            sessions = os.listdir(r)
            return 0, sessions
        else:
            return 1, 'no task_root'

    async def update_config(self):
        code, res = await run_shell('wget -c -t 10 "https://raw.githubusercontent.com/Qingluan/Map-Nodes/master/template.ini" -O- >  $HOME/.maper2.ini', background=False)
        if os.path.exists(os.path.expanduser("~/.maper2.ini")):
            os.rename(os.path.expanduser("~/.maper2.ini"), os.path.expanduser("~/.maper.ini"))
        self.conf = get_local_config()
        if not res:
            res = 'try to update maper.ini'
        return code,res

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
        elif op == 'clean':
            code, res = await self.uninstall()
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
        elif op == 'session':
            code, res = await self.get_sessions()
        elif op == 'cl':
            code, res = await self.clear_session()
        elif op == 'cla': 
            code, res = await self.clear_all()
        elif op == 'update':
            code, res = await self.check()
        elif op == 'ps':
            code, res = await self.check_tasks()
        elif op == 'info':
            code, res = await self.check_info()
        elif op == 'update-config':
            code, res = await self.update_config()
        elif op == 'sys-log':
            code, res = await self.get_sys_log()
        elif op == 'kill':
            assert 'app' in self._data
            assert 'session' in self._data
            session = self._data['session']
            app = self._data.get['app']
            date = self._data.get('date')
            if not date:
                date = datetime.datetime.now()
                date = "-".join([str(D.year),str(D.month), str(D.day)])
            code, res = await self.clear_task(app, session, date)
        elif op == 'ls':
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
        elif op == "down":
            session = self._data['session']
            root = os.path.join(self.conf['task_root'], session)
            res = await asyncio.get_event_loop().run_in_executor(self.__class__.Pocket, self.down_session_logs, root)
            code = 0
        elif op == 'upgrade-local':
            TaskData.save(None,None)
            version = update_and_start(self._pconf['server_port'])
            data = Task.build_json('', op="upgrade-local-fi", session=self._session)
            with open(os.path.expanduser("~/.mapper.json")) as fp:
                w = json.load(fp)
            time.sleep(12)
            loop = asyncio.get_event_loop()
            err_try = 0
            res = ''
            while 1:
                try:
                    res = await asyncio.wait_for(self.Sender(w, data,loop, no_read=True), timeout=2)
                    break
                except OSError as e:
                    if err_try > 3:
                        res = 'try bad' + str(e)
                        L("try restart updater: %d: %s" % (err_try, res))
                        break
                    err_try += 1
                    time.sleep(5)
                except asyncio.TimeoutError:
                    res = version
            L("version : ", version)
            res = version
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
        else:
            code = -1 
            res = HELP

        return  code, res
    
    def down_session_logs(self, root):
        res = {}
        for f in os.listdir(root):
            fname = os.path.join(root, f)
            if fname.endswith("log") or fname.endswith("err"):
                with open(fname) as fp:
                    content = fp.read()
                res[f] = content
        return res



    
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
    def build_jsons(cls, apps, op='run', year=None,mon=None,day=None, session=None,  **kargs):
        return [cls.build_json(app, op=op, year=year, mon=mon, day=day, session=session, **kargs) for app in apps]
    
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

