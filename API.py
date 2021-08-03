import requests, re, json, time
from random import randint
from typing import Union,List

CN_IP=( "110.42", "222.206", "220.180", "180.163", "113.100", #北京 山东 福建 上海 广东
        "125.83", "183.140", "49.78",   "106.230", "223.150") #重庆 浙江 江苏 江西 湖南

class BaseAPI:
    def __init__(self,timeout=5):
        self.timeout=timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.221 Safari/537.36 SE 2.X MetaSr 1.0",
        }
    
    def set_default_timeout(self,timeout=5):
        self.timeout=timeout
    
    def attach_cn_ip(self,headers:dict) -> dict:
        new_headers= dict(headers)
        ip=CN_IP[randint(0,len(CN_IP)-1)]+"."+str(randint(10,250))+"."+str(randint(10,250))
        new_headers["X-Real-IP"]=ip
        return new_headers

class BiliLiveAPI(BaseAPI):
    def __init__(self,cookies:Union[List[str],str],timeout=5):
        """B站直播相关API"""
        super().__init__(timeout)
        self.headers = dict(self.headers,
            Origin="https://live.bilibili.com",
            Referer="https://live.bilibili.com/")
        self.sessions = []
        self.csrfs = []
        self.rnd=int(time.time())
        if isinstance(cookies,str):    cookies=[cookies]
        for i in range(len(cookies)):
            self.sessions.append(requests.session())
            self.csrfs.append("")
            self.update_cookie(cookies[i],i)
    
    def get_room_info(self,roomid,timeout=None) -> dict:
        """获取直播间标题、简介等信息"""
        url="https://api.live.bilibili.com/xlive/web-room/v1/index/getInfoByRoom"
        params={"room_id":roomid}
        if timeout is None: timeout=self.timeout
        try:
            res=requests.get(url=url,headers=self.headers,params=params,timeout=timeout)
            return json.loads(res.text)
        except Exception as e:  raise e

    def get_danmu_config(self,roomid,number=0,timeout=None) -> dict:
        """获取用户在直播间内的可用弹幕颜色、弹幕位置等信息"""
        url="https://api.live.bilibili.com/xlive/web-room/v1/dM/GetDMConfigByGroup"
        params={"room_id":roomid}
        if timeout is None: timeout=self.timeout
        try:
            res=self.sessions[number].get(url=url,headers=self.headers,params=params,timeout=timeout)
            return json.loads(res.text)
        except Exception as e:  raise e
    
    def get_user_info(self,roomid,number=0,timeout=None) -> dict:
        """获取用户在直播间内的当前弹幕颜色、弹幕位置、发言字数限制等信息"""
        url="https://api.live.bilibili.com/xlive/web-room/v1/index/getInfoByUser"
        params={"room_id":roomid}
        if timeout is None: timeout=self.timeout
        try: 
            res=self.sessions[number].get(url=url,headers=self.headers,params=params,timeout=timeout)
            return json.loads(res.text)
        except Exception as e:  raise e
    
    def set_danmu_config(self,roomid,color=None,mode=None,number=0,timeout=None) -> dict:
        """设置用户在直播间内的弹幕颜色或弹幕位置
        :（颜色参数为十六进制字符串，颜色和位置不能同时设置）"""
        url="https://api.live.bilibili.com/xlive/web-room/v1/dM/AjaxSetConfig"
        data={
            "room_id": roomid,
            "color": color,
            "mode": mode,
            "csrf_token": self.csrfs[number],
            "csrf": self.csrfs[number],
        }
        if timeout is None: timeout=self.timeout
        try: 
            res=self.sessions[number].post(url=url,headers=self.headers,data=data,timeout=timeout)
            return json.loads(res.text)
        except Exception as e:  raise e
    
    def send_danmu(self,roomid,msg,number=0,timeout=None) -> dict:
        """向直播间发送弹幕"""
        url="https://api.live.bilibili.com/msg/send"
        data={
            "color": 16777215,
            "fontsize": 25,
            "mode": 1,
            "bubble": 0,
            "msg": msg,
            "roomid": roomid,
            "rnd": self.rnd,
            "csrf_token": self.csrfs[number],
            "csrf": self.csrfs[number],
        }
        if timeout is None: timeout=self.timeout
        try: 
            res=self.sessions[number].post(url=url,headers=self.headers,data=data,timeout=timeout)
            return json.loads(res.text)
        except Exception as e:  raise e
    
    def update_cookie(self,cookie:str,number=0) -> str:
        """更新账号Cookie信息
        :返回cookie中buvid3,SESSDATA,bili_jct三项的合并内容"""
        cookie = re.sub(r"\s+", "", cookie)
        mo1 = re.search(r"buvid3=([^;]+)", cookie)
        mo2 = re.search(r"SESSDATA=([^;]+)", cookie)
        mo3 = re.search(r"bili_jct=([^;]+)", cookie)
        buvid3,sessdata,bili_jct=mo1.group(1) if mo1 else "",mo2.group(1) if mo2 else "",mo3.group(1) if mo3 else ""
        cookie="buvid3=%s;SESSDATA=%s;bili_jct=%s"%(buvid3,sessdata,bili_jct)
        requests.utils.add_dict_to_cookiejar(self.sessions[number].cookies,{"Cookie": cookie})
        self.csrfs[number]=bili_jct
        return cookie

class NetEaseMusicAPI(BaseAPI):
    def __init__(self,timeout=5):
        """网易云音乐API"""
        super().__init__(timeout)

    def search_songs(self,keyword,limit=10,timeout=None,changeIP=False) -> dict:
        """按关键字搜索歌曲"""
        url="https://music.163.com/api/search/get/web"
        params= {
            "s": keyword,
            "limit": limit,
            "type": 1,
        }
        if timeout is None: timeout=self.timeout
        headers=self.attach_cn_ip(self.headers) if changeIP else self.headers
        try:
            res=requests.get(url=url,headers=headers,params=params,timeout=timeout)
            return json.loads(res.text)
        except Exception as e:  raise e
    
    def get_lyric(self,song_id,timeout=None,changeIP=False) -> dict:
        """根据歌曲ID获取歌词"""
        url="https://music.163.com/api/song/lyric"
        params=  {
            "id": song_id,
            "lv": -1,
            "tv": -1,
            # "kv":-1,
            # "os": "pc",
        }
        if timeout is None: timeout=self.timeout
        headers=self.attach_cn_ip(self.headers) if changeIP else self.headers
        try:
            res=requests.get(url=url,headers=headers,params=params,timeout=timeout)
            return json.loads(res.text)
        except Exception as e:  raise e
    
    def get_song_info(self,song_id,timeout=None,changeIP=False) -> dict:
        """根据歌曲ID获取歌曲信息"""
        url="https://music.163.com/api/song/detail"
        params= {
            "id": song_id,
            "ids": "[%s]"%str(song_id),
        }
        if timeout is None: timeout=self.timeout
        headers=self.attach_cn_ip(self.headers) if changeIP else self.headers
        try:
            res=requests.get(url=url,headers=headers,params=params,timeout=timeout)
            return json.loads(res.text)
        except Exception as e:  raise e
    
class QQMusicAPI(BaseAPI):
    def __init__(self,timeout=5):
        """QQ音乐API"""
        super().__init__(timeout)
        self.headers = dict(self.headers,
            Referer="https://y.qq.com/portal/player.html")

    def search_songs(self,keyword,limit=10,timeout=None,changeIP=False) -> dict:
        """按关键字搜索歌曲"""
        url="https://c.y.qq.com/soso/fcgi-bin/client_search_cp"
        params= {
            "w": keyword,
            "n": limit,
            "format": "json",
        }
        if timeout is None: timeout=self.timeout
        headers=self.attach_cn_ip(self.headers) if changeIP else self.headers
        try:
            res=requests.get(url=url,headers=headers,params=params,timeout=timeout)
            return json.loads(res.text)
        except Exception as e:  raise e
    
    def get_lyric(self,song_mid,timeout=None,changeIP=False) -> dict:
        """根据歌曲MID获取歌词"""
        url="https://c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric_new.fcg"
        params= {
            "songmid": song_mid,
            "nobase64": 1,
            "g_tk": 5381,
            "format": "json",
        }
        if timeout is None: timeout=self.timeout
        headers=self.attach_cn_ip(self.headers) if changeIP else self.headers
        try:
            res=requests.get(url=url,headers=headers,params=params,timeout=timeout)
            return json.loads(res.text)
        except Exception as e:  raise e
    
    def get_song_info(self,song_id,timeout=None,changeIP=False) -> dict:
        """根据歌曲ID获取歌曲信息"""
        url="https://c.y.qq.com/v8/fcg-bin/fcg_play_single_song.fcg"
        params= {
            "songid": song_id,
            "format": "json",
        }
        if timeout is None: timeout=self.timeout
        headers=self.attach_cn_ip(self.headers) if changeIP else self.headers
        try:
            res=requests.get(url=url,headers=headers,params=params,timeout=timeout)
            return json.loads(res.text)
        except Exception as e:  raise e

class JsdelivrAPI(BaseAPI):
    def __init__(self, timeout=5):
        """Jsdelivr公共CDN的API"""
        super().__init__(timeout)

    def get_latest_bili_live_shield_words(self,timeout=None) -> str:
        """获取最新的B站直播屏蔽词处理脚本（Github项目：FHChen0420/bili_live_shield_words）"""
        url="https://cdn.jsdelivr.net/gh/FHChen0420/bili_live_shield_words@main/BiliLiveShieldWords.py"
        if timeout is None: timeout=self.timeout
        try:
            res=requests.get(url,headers=self.headers,timeout=timeout)
            return res.text
        except Exception as e:  raise e
