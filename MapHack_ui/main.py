import curses
import os
from x_menu_src.menu import CheckBox, Application, Text,TextPanel, Menu, Stack
from x_menu_src.event import listener
from x_menu_src.log import log
from MapHack_src.config import get_local_config
import json
import time


CONF = get_local_config()
SERVER_ROOT = os.path.expanduser(CONF['client']['server_dir'])


class ConfigCheck(CheckBox):
    def update_when_cursor_change(self, item, ch):
        # conf_file = [1]]
        conf_file = os.path.join(SERVER_ROOT, item.split('] ',1)[1])
        log("checkbox:",conf_file)
        if conf_file and os.path.exists(conf_file):
            with open(conf_file) as fp:
                T = fp.read()
                # textPanel = Application.get_widget_by_id("show_config")
                # textPanel.reload_text(T, max_width=textPanel.end_x - textPanel.start_x)
                # textPanel.datas = T.split()
                # log(textPanel.datas)
                
                ConfigCheck.run_background(self.show, T)
                
                if hasattr(self, 'last_refresh'):

                    log('go',str(self.last_refresh))
                # self.show(T)
                # ()
    def show(self,text):
        # TextPanel.last_popup.endwin()
        
        # log(self.last_refresh)
        # curses.napms(3000)
        
        time.sleep(0.03)
        TextPanel.Cl()
        self.Redraw()
        # TextPanel.Popup(text, context=self, focus=False, width=len(text)+3)
        
        TextPanel.Popup(text, screen=self.screen,x=self.width//3, y=self.ix + 3, focus=False, width=len(text)+3)
        
    @listener(10)
    def do_actions(self):
        select = Stack.Popup(["log","attack", "change config","cancel"], context=self, exit_key=10)
        Stack.Cl()
        self.Redraw()
        ok_keys = [i for i in self.datas if self.datas[i]]
        if select == 'attack':
            res = Text.Popup(content=str(ok_keys), screen=self.screen, x=Application.width // 3,y = Application.height, max_height=3)
            log('write : ',res)

def main():
    app = Application()    
    all_config = {i: os.path.join(SERVER_ROOT, i) for i in  os.listdir(SERVER_ROOT)}
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



if __name__ == "__main__":
    main()