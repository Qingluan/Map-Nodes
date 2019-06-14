import asyncio
import curses
import os
from x_menu_src.menu import CheckBox, Application, Text,TextPanel, Menu, Stack
from x_menu_src.event import listener
from x_menu_src.log import log
from MapHack_src.config import get_local_config
from MapHack_src.task import Task
from MapHack_src.remote import Comunication
import json
import time


CONF = get_local_config()
SERVER_ROOT = os.path.expanduser(CONF['client']['server_dir'])

class IpMenu(Stack):

    def __init__(self, *args, **kargs):

        ips = os.listdir(SERVER_ROOT)
        super().__init__(ips,*args, **kargs)

    def show_log(self, ip ):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        w = json.load(open(os.path.join(SERVER_ROOT, ip)))
        log(w)
        msg = Task.build_json('',op='info',session='config')
        code,tag,msg = Comunication.SendOnce(w, msg, loop=loop)
        log(msg)
        sessions = msg['reply']['session']
        AppMenu.apps = msg['reply']['app']
        AppMenu.from_res(ip,sessions)


    def update_when_cursor_change(self, item, ch):
        if ch == 'l':
            self.show_log(item)


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

    def get_input(self, title):
        res = Text.Popup(content='', height=0,screen=self.screen, x=self.width // 4,y = self.ix+5, max_height=1, style='norm', title=title)
        self.Redraw()
        return res

    @listener(10)
    def on_enter(self):
        if self.id == 'log':
            self.show("wait .. to pull log")
            self.show_log_file(self.get_now_text())
        if self.id == 'sess':
            self.attack()

    def attack(self):
       target = self.get_input('set target [ip/host/url]')
       apps = CheckBox.Popup({i: False for i in AppMenu.apps},context=self, exit_key=10)
       apps = CheckBox.last_popup.get_options()
       CheckBox.Cl()
       self.Redraw()
       log(apps, target)
       AppMenu.run_background(self.run_task,target, [AppMenu.ip], apps, AppMenu.session, callback=self.callback)
       self.show("wait .. sending .. task")

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
        msg = Task.build_json(app,date=t,op='log',lines=300,session=session)
        code,tag, msg = Comunication.SendOnce(w, msg, loop=loop)
        cc = msg['reply']['log'] + "\n ===============\n" + msg['reply']['err_log']
        TextPanel.Popup(cc, x=self.start_x - self.width - 3, y=self.py + 5, screen=self.screen, exit_keys=[10])
        TextPanel.Cl()
        self.Redraw()


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
            logs = cls(logs_datas)
            Application.instance.add_widget(logs, weight=1)
        else:
            logs = Application.get_widget_by_id('log')
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
        session = session[0] if isinstance(session, list) else session
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        w = json.load(open(os.path.join(SERVER_ROOT, ip)))
        msg = Task.build_json('',op='check',session=session)
        code,tag, msg = Comunication.SendOnce(w, msg, loop=loop)
        return list(msg['reply'].keys())



def main():
    app = Application()    
    all_config = {i:False  for i in  os.listdir(SERVER_ROOT)}
    nodes_box = ConfigCheck(all_config, "configs")
    app.add_widget(nodes_box)
    conf_file = next(iter(all_config.values()))
    # if os.path.exists(conf_file):
    #     with open(conf_file) as fp:
    #         T = fp.read()
    #         print(T)
    #         app.add_widget(TextPanel(T, id="show_config", max_width=20))
    app.focus("configs")
    curses.wrapper(app.loop)

def main2():
    app = Application()
    ipm = IpMenu(id='ip')
    sess = AppMenu([],id='sess')
    logs = AppMenu([], id='log')
    app.add_widget(ipm,weight=0.5)
    app.add_widget(sess,weight=0.5)
    app.add_widget(logs,weight=1)
    app.focus('ip')
    curses.wrapper(app.loop)




if __name__ == "__main__":
    main2()
