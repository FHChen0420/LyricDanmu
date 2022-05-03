#coding=utf-8
import asyncio,websockets,zlib,json,re
from pubsub import pub
from socket import gaierror
from util import getTime

class BiliLiveWebSocket():
    __TL_PATTERN1=r"^【(?P<speaker>[^:：]{1,5})[:：](?P<content>[^】]+)"
    __TL_PATTERN2=r"^(?P<speaker>[^\u0592✉【][^【]{0,4})?【(?P<content>[^】]+)"
    __URI="wss://broadcastlv.chat.bilibili.com:2245/sub"
    __HEARTBEAT_PKG="00000010001000010000000200000001"
    __ENTERROOM_PKG="000000{pkgLen}0010000100000007000000017b22726f6f6d6964223a{roomid}7d"
    '''
    :协议头：
    00 00 00 __: 封包长度（协议头与数据包的长度之和）
    00 10:       协议头长度=16
    00 01:       协议版本=1
    00 00 00 __: 操作码（2=发送心跳包 7=进入房间）
    00 01:       sequence=1
    :数据包（可选）：
    7b 22 72 6f 6f 6d 69 64 22 3a ** 7d　　{"roomid":**}
    '''

    def __init__(self,roomid):
        self.__roomid=str(roomid)
        self.__ref_count=0
        self.__loop=asyncio.new_event_loop()
        self.__listening=False
        self.__closing=False

    async def __connect_to_room(self):
        pkg_len=hex(27+len(self.__roomid))[2:]
        roomid="".join(map(lambda x:hex(ord(x))[2:],list(self.__roomid)))
        error=False
        while self.__listening:
            try:
                async with websockets.connect(self.__URI) as websocket:
                    async def send_heart_beat():
                        while self.__listening:
                            try:
                                await websocket.send(bytes.fromhex(self.__HEARTBEAT_PKG))
                                await asyncio.sleep(30)
                            except asyncio.exceptions.CancelledError:
                                break
                    enter_room_pkg=self.__ENTERROOM_PKG.format(pkgLen=pkg_len, roomid=roomid)
                    await websocket.send(bytes.fromhex(enter_room_pkg))
                    hb_task=asyncio.create_task(send_heart_beat())
                    while self.__listening:
                        try:
                            res = await asyncio.wait_for(websocket.recv(),timeout=1)
                            self.__analyse_package(res)
                            if error:
                                error = False
                                print(f"[DEBUG] [{getTime()}] 与直播间{self.__roomid}的连接已恢复。")
                        except asyncio.exceptions.TimeoutError: pass
                        except websockets.ConnectionClosed: break
                    hb_task.cancel()
            except (gaierror,ConnectionRefusedError,asyncio.exceptions.TimeoutError):
                if not error:
                    error = True
                    print(f"[DEBUG] [{getTime()}] 与直播间{self.__roomid}的连接已中断。")
                await asyncio.sleep(2)
            except RuntimeError:
                pass
            except BaseException as e:
                print(f"[ERROR] [{getTime()}] 与直播间{self.__roomid}的连接发生严重异常。\n TYPE={type(e)} DESC={str(e)}")
                break

    def __analyse_package(self,raw_data):
        packetLen = int(raw_data[:4].hex(),16)
        ver = int(raw_data[6:8].hex(),16)
        op = int(raw_data[8:12].hex(),16)
        if len(raw_data)>packetLen:
            self.__analyse_package(raw_data[:packetLen])
            self.__analyse_package(raw_data[packetLen:])
            return
        if ver==2:
            raw_data = zlib.decompress(raw_data[16:])
            self.__analyse_package(raw_data)
            return
        if ver==0 and op==5:
            try:
                jd = json.loads(raw_data[16:].decode("utf-8", errors="ignore"))
                if jd["cmd"]!="DANMU_MSG": return
                info=jd["info"]
                mo=re.match(self.__TL_PATTERN1,info[1])
                if mo is None:
                   mo=re.match(self.__TL_PATTERN2,info[1]) 
                if mo is not None:
                    pub.sendMessage(
                        "ws_recv",
                        roomid=self.__roomid,
                        speaker="" if mo.group("speaker") is None else mo.group("speaker"),
                        content=mo.group("content"),
                        #uid=info[2][0],
                        #uname=info[2][1],
                        #ts=info[0][4]/1000,
                    )
            except RuntimeError:
                return
            except BaseException as e:
                print(f"[DEBUG] [{getTime()}] 数据包解析失败。\n DATA={jd}\n TYPE={type(e)} DESC={str(e)}")
    
    def ChangeRefCount(self,n):
        origin_ref_count=self.__ref_count
        self.__ref_count+=n
        if n>0 and origin_ref_count==0:
            pub.sendMessage("ws_start",roomid=self.__roomid) #在新的线程中调用self.Start()
        if n<0 and self.__ref_count==0:
            self.Stop()

    def Start(self):
        self.__listening=True
        if not self.__closing:
            print(f"[ INFO] [{getTime()}] 已连接到直播间{self.__roomid}。")
            self.__loop.run_until_complete(self.__connect_to_room())
            self.__closing=False
            print(f"[ INFO] [{getTime()}] 已断开与直播间{self.__roomid}的连接。")

    def Stop(self):
        self.__closing=True
        self.__listening=False
