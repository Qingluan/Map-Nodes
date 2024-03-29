import asyncio
import logging
import os
import struct
import json
from MapHack_src.cryptor import  Cryptor
from MapHack_src.task import  Task
from MapHack_src.log import  L
from base64 import  b64encode, b64decode

AUTH = 0
CON = 1
END = 2
test_conf = {"server":"localhost","server_port":9999, "method":"aes-256-cfb","password":"asdf"}

class R:
    def __init__(self, conf):
        self.conf = conf

    async def handle_loop(self, reader, writer):
        cc = Comunication(self.conf)
        # code, res = await Task.Check()
        # L(res)
        while 1:
            if cc.state == AUTH:
                addr = writer.get_extra_info('peername')
                logging.debug("from %s " % str(addr))
                code, msg = await cc.auth(reader, writer)
                if code != 0:
                    break
                L("authed:", code, cc.auth_tag)
            else:
                code, msg = await cc.trans(reader, writer)
            if code != 0:
                break

        
        print("Close the client socket")
        # await cc.reply("close", writer)
        writer.close()
class Data:
    @classmethod
    def unpatch(cls, data):
        t = data[:16]
        l = struct.unpack("q", data[16:24])[0]
        d = data[24:24+ l]
        if len(d) != l:
            return  1,t,"len error"
        return  0,t,d
    
    @classmethod
    def patch(cls, tag, data):
        l = len(data)
        return tag + struct.pack('q',l) + data
    
    @classmethod
    def reply(cls, msg,ip=None, **kargs):
        if isinstance(msg, bytes):
            msg = msg.decode()
        kargs.update({
            'reply':msg,
        })
        if ip:
            kargs['ip'] = ip
        return json.dumps(kargs).encode('utf-8')


class Comunication:
    def __init__(self, conf, is_local=False):
        self._crypt = Cryptor(conf['password'], conf['method'])
        self._data_wait_write = []
        self.state = AUTH
        self._is_local = is_local
        self.s_tag = os.urandom(8)
        self.c_tag = os.urandom(8)
        self.auth_tag = b''
        self._conf = conf

    async def auth(self, reader,writer):
        if self._is_local:
            c_tag = self.c_tag
            writer.write(c_tag)
            await writer.drain()
            s_tag = await reader.read(8)
        else:
            c_tag = await reader.read(8)
            s_tag = self.s_tag
            writer.write(s_tag)
            await writer.drain()
        logging.debug(c_tag)
        logging.debug(s_tag)
        self.auth_tag = s_tag + c_tag
        if len(self.auth_tag) == 16:
            self.state = CON
            self._reader = reader
            self._writer = writer
            return  0, b'ok'
        return  1, b'shit'
    
    async def trans(self, reader, writer):
        logging.debug("wait")
        code, t, data = await self.recive(reader)
        if code == 0 and t == self.auth_tag:
            reply_msg = await self.handle_data(data)
            await self.reply(reply_msg)
            return  0, "ok"
        else:
            return 1, 'tag error'
    
    async def reply(self, reply_msg, writer=None, **kargs):
        if not writer:
            writer = self._writer
        data = Data.patch(self.auth_tag, Data.reply(reply_msg,ip=self._conf['server'], **kargs))
        en_data = self._crypt.encrypt(data)
        writer.write(en_data)
        writer.write_eof()
        return await writer.drain()

    async def recive(self, reader=None):
        if not reader:
            reader = self._reader
        data = await reader.read()
        # logging.info("%s" % data)
        if not data:
            return  1, None, None
        de = self._crypt.decrypt(data)
        code,t,data = Data.unpatch(de)
        logging.debug("R:%s" % data)
        data = data if isinstance(data, str) else data.decode()
        return  code, t, json.loads(data)

    async def handle_data(self, data):
        # try:
        code, res = await Task.from_json(data, conf=self._conf, sender=self.sendone)
        return  res
        # except  Exception as e:
            # return str(e)
        

    @classmethod
    async def Con(cls, conf, loop=None):
        if not loop:
            loop = asyncio.get_event_loop()
        con = cls(conf, is_local=True)
        reader, writer = await asyncio.open_connection(host=conf['server'],
                            port=conf['server_port'],loop=loop)
        
        code, auth_msg = await con.auth(reader, writer)
        if code == 0:
            return con, reader,writer
        else:
            raise Exception("connect failed: %r"%auth_msg )

    @classmethod
    def SendMul(cls, confs, msgs, loop=None, callback=None):
        fs = []
        for i,msg in enumerate(msgs):
            conf = confs[i % len(confs)]
            L({conf['server']:msg})
            fs.append(test_con_callback(conf, msg,loop, callback=callback))

        fu = asyncio.gather(*fs)
        return loop.run_until_complete(fu)

    
    @classmethod
    def SendOnce(cls, conf, msg, loop=None):
        if not loop:
            loop = asyncio.get_event_loop()
        return loop.run_until_complete(test_con(conf, msg, loop))

    async def sendone(self, conf, msg, loop, no_read=False):
        return await test_con(conf, msg, loop, no_read=no_read) 
    


def run_server(conf):
    loop = asyncio.get_event_loop()
    r = R(conf)
    coro = asyncio.start_server(r.handle_loop, conf['server'], conf['server_port'], loop=loop)
    server = loop.run_until_complete(coro)

    # Serve requests until Ctrl+C is pressed
    print('Serving on {}'.format(server.sockets[0].getsockname()))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    # Close the server
    server.close()
    loop.run_until_complete(server.wait_closed())
    loop.close()




async def test_con(conf, msg,loop, no_read=False):
    try:    
        con, R, W = await Comunication.Con(conf, loop=loop)
    except ConnectionRefusedError:
        return 1, '',{"ip":conf['server'] , "reply":conf['server'] + " can't connect", 'code':1}
    await con.reply("msg", **msg)
    if no_read:
        return 0,None,{'msg':'no wait', 'ip':conf['server'], 'code':0}
    try:
        code, t, data = await asyncio.wait_for(con.recive(), 20)
        if isinstance(data,dict):
            data['ip'] = conf['server']
            data['code'] = code
        elif isinstance(data, str):
            data = {'ip':conf['sever'], 'reply':data, 'code' :0 }
        else:
            L(type(data))
            print(data)
        if not data:
            return code, t, 'no data recive you can check version by --op info'
        if 'reply' not in data:
            return code,t,data
        if not data['reply']:
            return code, t ,{'ip':conf['server'], 'reply':'', 'code' :0 }
        if 'log' in data['reply']:
            try:
                data['reply']['log'] = b64decode(data['reply']['log'].encode()).decode()
                data['reply']['err_log'] = b64decode(data['reply']['err_log'].encode()).decode()
            except Exception as e:
                data['code'] = 1
                return code, t, data
        return code, t, data
    except asyncio.TimeoutError:
        return 1, '', {'ip':conf['server'],'reply':'Timeout', 'code':1}

async def test_con_callback(conf, msg,loop, no_read=False, callback=None):
    if not callback:
        return await test_con(conf, msg, loop, no_read=no_read)
    else:
        code,tag, res = await test_con(conf, msg, loop, no_read=no_read)
        await(callback(code, tag,res))
        return code,tag, res

def test(conf):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test_con(conf, loop))

if __name__ == "__main__":
    
    run_server(test_conf)
