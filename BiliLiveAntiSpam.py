#coding=utf-8
import zlib
import json
import asyncio
import websockets
from pubsub import pub
from socket import gaierror
from util import getTime

class BiliLiveAntiSpam():
    def __init__(self,roomid,spamChecker):
        pub.subscribe(self.OnClose,"close_ws")
        self.roomid=roomid
        self.checker=spamChecker
        self.running=True
        self.hb_task=None
        asyncio.new_event_loop().run_until_complete(self.GetWebSocketData())

    async def GetWebSocketData(self):
        uri = "wss://broadcastlv.chat.bilibili.com:2245/sub"
        data_raw="000000{headerLen}0010000100000007000000017b22726f6f6d6964223a{roomid}7d"
        error=False
        while self.running:
            self.CancelHBTask()
            try:
                async with websockets.connect(uri) as websocket:
                    data=data_raw.format(headerLen=hex(27+len(self.roomid))[2:], roomid="".join(map(lambda x:hex(ord(x))[2:],list(self.roomid))))
                    await websocket.send(bytes.fromhex(data))
                    self.hb_task=asyncio.create_task(self.SendHeartBeat(websocket))
                    print("%s│<[连接到直播间%s]>"%(getTime(),self.roomid))
                    error=False
                    while self.running:
                        try:
                            res = await asyncio.wait_for(websocket.recv(),timeout=1)
                            self.AnalyseData(res)
                            if error:
                                error = False
                                print("%s│<[连接恢复]>"%getTime())
                        except asyncio.exceptions.TimeoutError: pass
                        except websockets.ConnectionClosed: break
                        # except Exception as e:
                        #     print("%s│<[%s]>"%(getTime(),type(e)),e)
                        #     break
            except ConnectionRefusedError:
                if not error:
                    print("%s│<[ConnectionRefusedError]>"%getTime())
                    error = True
                await asyncio.sleep(2)
            except gaierror:
                if not error:
                    print("%s│<[GetAddrInfoError]>"%getTime())
                    error = True
                await asyncio.sleep(2)
            except RuntimeError:
                pass
            except Exception as e:
                print(type(e),e)
                print("%s│<[已终止与直播间%s的链接]>"%(getTime(),self.roomid))
                break

    async def SendHeartBeat(self,websocket):
        hb = "00000010001000010000000200000001"
        while self.running:
            try:
                await websocket.send(bytes.fromhex(hb))
                await asyncio.sleep(30)
            except Exception:
                break

    def AnalyseData(self,raw_data):
        packetLen = int(raw_data[:4].hex(),16)
        ver = int(raw_data[6:8].hex(),16)
        op = int(raw_data[8:12].hex(),16)
        if len(raw_data)>packetLen:
            self.AnalyseData(raw_data[:packetLen])
            self.AnalyseData(raw_data[packetLen:])
            return
        if ver==2:
            raw_data = zlib.decompress(raw_data[16:])
            self.AnalyseData(raw_data)
            return
        if ver==0 and op==5:
            try:
                jd = json.loads(raw_data[16:].decode("utf-8", errors="ignore"))
                if jd["cmd"]!="DANMU_MSG": return
                pub.sendMessage("test",roomid=self.roomid)
                info=jd["info"]
                uid,uname,ts,msg,formal=info[2][0],info[2][1],info[0][4]/1000,info[1],info[2][5]>=10000
                level,signature=self.checker.check({"uname":uname,"content":msg.replace(" ","")})
                if level==2 and not formal:
                    pub.sendMessage("spam",roomid=self.roomid,uid=uid,signature=signature)
            except RuntimeError:
                return
            except Exception as e:
                print("WS解析错误",type(e),e)
    
    def CancelHBTask(self):
        try:
            if self.hb_task is not None and not self.hb_task.cancelled():
                self.hb_task.cancel()
        except Exception as e:
            print("cancel hb_task error:",type(e),e)
    
    def OnClose(self):
        self.running=False
        self.CancelHBTask()
