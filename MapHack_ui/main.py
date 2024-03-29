import asyncio
import curses
import os
import configparser
from x_menu_src.menu import CheckBox, Application, Text,TextPanel, Menu, Stack, ColorConfig
from x_menu_src.event import listener
from x_menu_src.log import log
from MapHack_src.config import get_local_config
from MapHack_src.task import Task
from MapHack_src.remote import Comunication
from MapHack_src.selector import build_tasks, run_tasks, select, pull_all_ini
import json
import time
import tempfile
from subprocess import call


CONF = get_local_config()
SERVER_ROOT = os.path.expanduser(CONF['client']['server_dir'])
SESSION_ROOT = "/tmp/sesisons/"
if not  os.path.exists(SESSION_ROOT):
    os.mkdir(SESSION_ROOT)

def editor(content):
    EDITOR = os.environ.get('EDITOR','vim') #that easy!
    with tempfile.NamedTemporaryFile(suffix=".tmp") as tf:
        tf.write(content.encode())
        tf.flush()
        call([EDITOR, tf.name])

def _show(text, context):
        time.sleep(0.03)
        TextPanel.Cl()
        if hasattr(context, 'Redraw'):
            context.Redraw()
        TextPanel.Popup(text, screen=context.screen,x=context.width//2, y=context.ix + 10, focus=False, width=len(text)+3)

def Show( text, context):
    Stack.run_background(_show, text, context)


def ShowFi(context):
    TextPanel.Cl()
    if hasattr(context, 'Redraw'):
        context.Redraw()

class IpMenu(CheckBox):
    all_ips = None
    infos = {}
    sessions = None
    def __init__(self, *args, **kargs):

        ips = os.listdir(SERVER_ROOT)
        ips = {i:True for i in ips}
        super().__init__(ips,*args, **kargs)
        self.__class__.all_ips = ips

    def show_log(self, ip ,refresh=False):
        if refresh:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            w = json.load(open(os.path.join(SERVER_ROOT, ip)))
            log(w)
            msg = Task.build_json('',op='info',session='config')
            code,tag,msg = Comunication.SendOnce(w, msg, loop=loop)
            log(msg)
            sessions = msg['reply']['session']
        else:
            if ip in IpMenu.infos:
                AppMenu.apps = IpMenu.infos[ip]['app']
                sessions = IpMenu.infos[ip]['session']
            else:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                w = json.load(open(os.path.join(SERVER_ROOT, ip)))
                msg = Task.build_json('',op='info',session='config')
                code,tag,msg = Comunication.SendOnce(w, msg, loop=loop)
                log(msg)
                sessions = msg['reply']['session']
                AppMenu.apps = msg['reply']['app']
        AppMenu.from_res(ip,sessions)


    def update_when_cursor_change(self, item, ch):
        # if ch == 'l':
        if '[' in item:
            item = item.split("]",1)[1].strip()
        self.show_log(item)

    @listener('c')
    def clear_session(self):
        res = Stack.Popup(['no','yes'], context=self, exit_key=10)
        if res != 'yes':
            return 
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        ips = self.get_options()
        confs = list(select(ips))
        msgs = list(build_tasks(confs, op='cla', session='config'))
        Show('delete all session in this ',self)
        run_tasks(list(confs), list(msgs),callback=self.callback)
        ShowFi(self)
        self.__class__.Refresh(self)


    @listener('r')
    def refresh(self):
        self.__class__.Refresh(self)
        ip = self.get_now_text()
        if '[' in ip:
            ip = ip.split("]",1)[1].strip()
        log(IpMenu.infos)
        session = IpMenu.infos[ip]['session']
        AppMenu.from_res(ip, session)

    @listener('v')
    def vi_server_ini(self):
        w = json.load(open(os.path.join(SERVER_ROOT, self.get_now_text().strip())))
        data = Task.build_json('',op='get-ini', session='config')
        res = Comunication.SendOnce(w, data)
        content = editor(res[2]['reply'])
        data = Task.build_json('', op="sync-ini", session='config', content=content)
        Stack.run_background(Comunication.SendOnce, w,data)

    @listener('t')
    def on_attack(self):
        self.attack()


    @classmethod
    def Refresh(cls, context):
        try:
            ips = cls.all_ips if cls.all_ips else []
            confs = list(select('.'))
            msgs = list(build_tasks(confs, op='info', session='config'))
            Show("wait ... sync all infos", context)
            for code,tag, res in run_tasks(confs, msgs):
                if code == 0:
                    ip = res['ip']
                    cls.infos[ip] = res['reply']
            with open("/tmp/tmp_session_info.json", 'w') as fp:
                json.dump(cls.infos, fp)
            ShowFi(context)
        except Exception as e:
            log(str(e))

    def attack(self):
        ips = self.get_options()
        target = self.get_input('set target split by "," ')
        session = self.get_input('set session')
        session = session.replace(' ', '_')
        apps = CheckBox.Popup({i: False for i in AppMenu.apps},context=self, exit_key=10)
        apps = CheckBox.last_popup.get_options()
        CheckBox.Cl()
        self.Redraw()
        log(apps, target)
        confs = list(select(ips))
        msgs = list(build_tasks(confs,targets=target.split(","),apps=apps,session=session))
        Show("wait .. sending .. task", self)
        log(msgs)
        run_tasks(list(confs), list(msgs),callback=self.callback)
        ShowFi(self)

    async def callback(self,code,tag,res):
        log(code,res)



class AppMenu(Stack):
    instance = None
    ip = None
    session = None
    sessions = None
    apps = None

    def update_when_cursor_change(self, item, ch):
        if ch in 'jk':
            if self.id == 'sess':
                log(AppMenu.ip, item)
                AppMenu.from_res(AppMenu.ip, item)
                AppMenu.session = item
        if ch in 'l':
            if self.id == 'log':
                self.show("wait .. to pull log")
                self.show_log_file(item)

    def draw_text(self,row,col, text, max_width=None, attrs=1, prefix='',prefix_attrs=None, mark=False):
        if_run = mark
        if AppMenu.session and AppMenu.ip:
            log_file = AppMenu.session + "/"+ text.strip()
            if not mark:
                if_run = IpMenu.infos[AppMenu.ip]['ps'].get(log_file, False)
                if if_run:
                    attrs = ColorConfig.get('green')
                log(log_file, if_run)
            else:
                if_run = mark

        log(attrs)
        super().draw_text(row, col, text, max_width=max_width, attrs=attrs, prefix=prefix,mark=if_run)

    def get_input(self, title):
        res = Text.Popup(content='', height=0,screen=self.screen, x=self.width // 4,y = self.ix+5, max_height=1, style='norm', title=title)
        self.Redraw()
        return res

    @listener(10)
    def on_enter(self):
        if self.id == 'log':
            self.show("wait .. to pull log")
            self.show_log_file(self.get_now_text())

    @listener('r')
    def refresh(self):
        IpMenu.Refresh(self)


    def callback(self, *msgs):
        self.show('\n'.join([str(i['reply']) for i in msgs]))

    def run_task(self,target, servers, apps, session, op='run', **kwargs):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        msgs = Task.build_jsons(apps,op=op,session=session,ip=target,option='',background=True,**kwargs)
        log(msgs)
        ws = []
        for s in servers:
            with open(os.path.join(SERVER_ROOT,s)) as fp:
                w = json.load(fp)
                ws.append(w)
        mul_res = Comunication.SendMul(ws, msgs, loop=loop)
        log(mul_res)
        msgs = [i[-1] for i in mul_res]
        return msgs

    def show_log_file(self, log_file):
        ip = AppMenu.ip
        session = AppMenu.session
        if '-' not in log_file:
            return
        app, t = log_file.split("-",1)
        t = t.split(".")[0]
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        w = json.load(open(os.path.join(SERVER_ROOT, ip)))
        msg = Task.build_json(app,date=t,op='log',line=300,session=session)
        code,tag, msg = Comunication.SendOnce(w, msg, loop=loop)
        try:
            cc = msg['reply']['log'] + "\n ===============\n" + msg['reply'].get('err_log', "")
            log('err get:',cc)
        except (KeyError,TypeError) as e:
            cc = str(msg['reply'])
            log('err get:',cc)
        TextPanel.Popup(cc, x=self.start_x - self.width - 3,max_height=Application.height - self.px -5, width=80, y=self.py + 5, screen=self.screen, exit_keys=[10])
        TextPanel.Cl()
        self.Redraw()
        ShowFi(self)

    @classmethod
    def from_res(cls,ip, sessions):
        if isinstance(sessions, list):
            AppMenu.sessions = sessions

        logs_datas = cls.get_logs(ip,sessions)
        if 'sess' not in Application.widgets:
            sess = cls(sessions, id='sess')
            AppMenu.ip = ip
            Application.instance.add_widget(sess, weight=1)
        else:
            sess = Application.get_widget_by_id('sess')
            sess.datas = AppMenu.sessions
            AppMenu.ip = ip
        if 'log' not in Application.widgets:
            logs = cls([i for i in logs_datas if i.endswith('log')])
            Application.instance.add_widget(logs, weight=1)
        else:
            logs = Application.get_widget_by_id('log')
            logs_datas = [i for i in logs_datas if i.endswith('log')]
            if len(logs_datas) ==0:
                logs_datas = ['no data']
            logs.datas = logs_datas
        Application.instance.refresh(clear=True)


    def _show(self,text):
        time.sleep(0.03)
        TextPanel.Cl()
        self.Redraw()
        TextPanel.Popup(text, screen=self.screen,x=self.width//2, y=self.ix + 10, focus=False, width=len(text)+3)

    def show(self, text):
        Stack.run_background(self._show, text)


    @classmethod
    def get_logs(cls, ip,session):
        if ip in IpMenu.infos:
            session = session[0] if isinstance(session, list) else session
            res = IpMenu.infos[ip]
            logs = []
            for log in res['ps']:
                if log.startswith(session):
                    # logs[log.split("/")[0]] = res['ps'][log]
                    logs.append(log.split("/")[1])
            return logs
        else:
            session = session[0] if isinstance(session, list) else session
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            w = json.load(open(os.path.join(SERVER_ROOT, ip)))
            msg = Task.build_json('',op='check',session=session)
            code,tag, msg = Comunication.SendOnce(w, msg, loop=loop)
            return list(msg['reply'].keys())



def main():
    confs = list(select(''))
    # pull_all_ini(confs)
    if os.path.exists("/tmp/tmp_session_info.json"):
        with open("/tmp/tmp_session_info.json") as fp:
            IpMenu.infos = json.load(fp)

    app = Application()
    ipm = IpMenu(id='ip')
    sess = AppMenu([],id='sess')
    logs = AppMenu([], id='log')
    app.add_widget(ipm,weight=0.5)
    app.add_widget(sess,weight=0.5)
    app.add_widget(logs,weight=1)
    app.focus('ip')
    Show("wait .. to start ", ipm)
    IpMenu.Refresh(ipm)
    ShowFi(ipm)
    curses.wrapper(app.loop)




if __name__ == "__main__":
    main()
