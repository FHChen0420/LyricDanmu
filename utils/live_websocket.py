#coding=utf-8
import asyncio
import json
import re
import aiohttp
import brotli

from pubsub import pub

from utils.util import getTime, logDebug


class BiliLiveWebSocket():
    __TL_PATTERN1=r"^【(?P<speaker>[^:：]{1,5})[:：](?P<content>[^】]+)"
    __TL_PATTERN2=r"^(?P<speaker>[^\u0592✉【][^【]{0,4})?【(?P<content>[^】]+)"
    __URI="wss://{host}:{wss_port}/sub"
    __HEARTBEAT_PKG="00000010001000010000000200000001"
    __ENTERROOM_HEADER="{:0>8x}001000010000000700000001"
    __URL_GETDANMUINFO="https://api.live.bilibili.com/xlive/web-room/v1/index/getDanmuInfo?id={roomid}&type=0"
    __UA={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36 Edg/115.0.1901.188"}
    __TIMEOUT=aiohttp.ClientTimeout(5)
    '''
    :协议头：
    __ __ __ __: 封包长度（协议头与数据包的长度之和）
    00 10:       协议头长度=16
    00 01:       协议版本=1
    __ __ __ __: 操作码（2=发送心跳包 7=进入房间）
    00 01:       sequence=1
    :后续接数据包内容
    '''

    def __init__(self,roomid):
        self.__roomid=str(roomid)
        self.__ref_count=0
        self.__loop=asyncio.new_event_loop()
        self.__listening=False
        self.__closing=False
        self.__error=False
        self.__hb_task=None

    async def __connect_to_room(self):
        self.__error=False
        while self.__listening:
            try:
                # 获取直播间弹幕服务器地址列表以及token
                token = ""
                async with aiohttp.ClientSession(timeout=self.__TIMEOUT) as session:
                    async with session.get(self.__URL_GETDANMUINFO.format(roomid=self.__roomid)) as res:
                        data = await res.json()
                        if data["code"]==0:
                            token = data["data"]["token"]
                            server = data["data"]["host_list"][0]
                            uri = self.__URI.format(host=server["host"],wss_port=server["wss_port"])
                        else:
                            print("获取弹幕服务器地址失败")
                param={ # 建立连接时附带的数据包
                    "uid": 0,
                    "roomid": int(self.__roomid),
                    "protover": 3,
                    "platform": "web",
                    "type": 2,
                    "key": token
                }
                body = json.dumps(param).encode().hex()
                async with aiohttp.ClientSession(timeout=self.__TIMEOUT) as session:
                    async with session.ws_connect(uri, headers=self.__UA) as websocket:
                        '''定义 心跳包定时发送任务'''
                        async def send_heart_beat():
                            count = 0
                            while self.__listening:
                                try:
                                    await websocket.send_bytes(bytes.fromhex(self.__HEARTBEAT_PKG))
                                    count = 0
                                    await asyncio.sleep(30)
                                except asyncio.exceptions.CancelledError:
                                    break
                                except ConnectionResetError as e:
                                    count += 1
                                    if count <= 5:
                                        print(f"[DEBUG] [{getTime()}] 向直播间{self.__roomid}的心跳包发送失败。TYPE={type(e)}")
                                    else:
                                        print(f"[DEBUG] [{getTime()}] 已中止向直播间{self.__roomid}发送心跳包任务。")
                                        logDebug(f"[BiliLiveWebSocket.send_heart_beat] ROOMID={self.__roomid} DESC=已中止发送心跳包")
                                        break
                                    await asyncio.sleep(5)
                                except BaseException as e:
                                    print(f"[DEBUG] [{getTime()}] 向直播间{self.__roomid}的心跳包发送失败。TYPE={type(e)}")
                                    logDebug(f"[BiliLiveWebSocket.send_heart_beat] ROOMID={self.__roomid} DESC={e}")
                                    await asyncio.sleep(5)
                        # 任务定义结束
                        # 建立连接
                        enter_room_pkg = self.__ENTERROOM_HEADER.format(16+len(body)//2) + body
                        await websocket.send_bytes(bytes.fromhex(enter_room_pkg)) # 发送进入房间请求
                        self.__hb_task=asyncio.create_task(send_heart_beat()) # 执行心跳包定时发送任务
                        while self.__listening:
                            try:
                                res = await asyncio.wait_for(websocket.receive_bytes(),timeout=1)
                                self.__analyse_package(res) # 解析接收到的数据
                                if self.__error:
                                    self.__error = False
                                    pub.sendMessage("ws_error",roomid=self.__roomid,count=-1)
                                    print(f"[DEBUG] [{getTime()}] 与直播间{self.__roomid}的连接已恢复。")
                            except asyncio.exceptions.TimeoutError: pass
                            except aiohttp.ClientConnectionError: break
                        self.__hb_task.cancel()
            except (aiohttp.ClientConnectorError, asyncio.exceptions.TimeoutError, TypeError):
                if not self.__error:
                    self.__error = True
                    pub.sendMessage("ws_error",roomid=self.__roomid,count=1)
                    print(f"[DEBUG] [{getTime()}] 与直播间{self.__roomid}的连接已中断。")
                await asyncio.sleep(2)
            except RuntimeError:
                pass
            except BaseException as e:
                if not self.__error:
                    self.__error = True
                    pub.sendMessage("ws_error",roomid=self.__roomid,count=1)
                print(f"[DEBUG] [{getTime()}] 与直播间{self.__roomid}的连接发生未知异常。\n TYPE={type(e)}")
                logDebug(f"[BiliLiveWebSocket.__connect_to_room] ROOMID={self.__roomid} DESC={e}")
                await asyncio.sleep(5)

    def __analyse_package(self,raw_data):
        package_len = int(raw_data[:4].hex(),16)    # 封包长度（协议头+数据包，其中协议头固定长16）
        ver = int(raw_data[6:8].hex(),16)           # 数据包协议（0正常，1心跳包，2zlib压缩，3brotli压缩）
        op = int(raw_data[8:12].hex(),16)           # 操作码（3心跳包回应，5业务数据回应，8认证数据回应，等等）
        if op==3: # 忽略心跳包回应数据
            return
        if len(raw_data)>package_len: # 对整合过的数据包进行划分
            self.__analyse_package(raw_data[:package_len])
            self.__analyse_package(raw_data[package_len:])
            return
        if ver==3: # 对压缩过的字节码进行解压
            raw_data = brotli.decompress(raw_data[16:])
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
                        #timestamp=info[0][4]/1000,
                    )
            except RuntimeError:
                return
            except BaseException as e:
                print(f"[DEBUG] [{getTime()}] 数据包解析失败。\n DATA={jd}\n TYPE={type(e)}")
                logDebug(f"[BiliLiveWebSocket.__analyse_package] DATA={jd} DESC={e}")
    
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
            if self.__error:
                pub.sendMessage("ws_error",roomid=self.__roomid,count=-1)
            print(f"[ INFO] [{getTime()}] 已主动断开与直播间{self.__roomid}的连接。")

    def Stop(self):
        self.__closing=True
        self.__listening=False
        if self.__hb_task:
            self.__hb_task.cancel()
