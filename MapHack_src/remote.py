import asyncio
import logging
import os
import struct
import json
from MapHack_src.cryptor import  Cryptor
from MapHack_src.task import  Task
from MapHack_src.log import  L

AUTH = 0
CON = 1
END = 2
test_conf = {"server":"localhost","server_port":9999, "method":"aes-256-cfb","password":"asdf"}

class R:
    def __init__(self, conf):
        self.conf = conf

    async def handle_loop(self, reader, writer):
        cc = Comunication(self.conf)
        code, res = await Task.Check()
        L(res)
        while 1:
            if cc.state == AUTH:
                addr = writer.get_extra_info('peername')
                logging.info("from %s " % str(addr))
                code, msg = await cc.auth(reader, writer)
                print("what:", code)
            else:
                code, msg = await cc.trans(reader, writer)
                print("s:", msg)
            if code != 0:
                break

        
        print("Close the client socket")
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
    def reply(cls, msg, **kargs):
        if isinstance(msg, bytes):
            msg = msg.decode()
        kargs.update({
            'reply':msg,
        })
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
        logging.info(c_tag)
        logging.info(s_tag)
        self.auth_tag = s_tag + c_tag
        if len(self.auth_tag) == 16:
            self.state = CON
            self._reader = reader
            self._writer = writer
            return  0, b'ok'
        return  1, b'shit'
    
    async def trans(self, reader, writer):
        logging.info("wait")
        code, t, data = await self.recive(reader)
        if code == 0 and t == self.auth_tag:
            reply_msg = await self.handle_data(data)
            await self.reply(reply_msg)
            return  0, "ok"
        else:
            return 1, 'tag error'
    
    async def reply(self, reply_msg, **kargs):
        data = Data.patch(self.auth_tag, Data.reply(reply_msg, **kargs))
        en_data = self._crypt.encrypt(data)
        self._writer.write(en_data)
        self._writer.write_eof()
        return await self._writer.drain()

    async def recive(self, reader=None):
        if not reader:
            reader = self._reader
        data = await reader.read()
        # logging.info("%s" % data)
        if not data:
            return  1, None, None
        de = self._crypt.decrypt(data)
        code,t,data = Data.unpatch(de)
        logging.info("R:%s" % data)
        return  code, t, json.loads(data.decode())

    async def handle_data(self, data):
        # try:
        code, res = await Task.from_json(data)
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
    def SendOnce(cls, conf, msg):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(test_con(conf, msg, loop))
    


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

async def test_con(conf, msg,loop):
    
    con, R, W = await Comunication.Con(conf, loop=loop)
    await con.reply("msg", **msg)
    res = await con.recive()
    return res

def test(conf):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test_con(conf, loop))

if __name__ == "__main__":
    
    run_server(test_conf)