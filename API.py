import requests
import re
import json
import time
from random import randint

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
    
    def attach_cn_ip(self,headers):
        new_headers= dict(headers)
        ip=CN_IP[randint(0,len(CN_IP)-1)]+"."+str(randint(10,250))+"."+str(randint(10,250))
        new_headers["X-Real-IP"]=ip
        return new_headers

class BiliLiveAPI(BaseAPI):
    def __init__(self,cookies,timeout=5):
        super().__init__(timeout)
        self.headers = dict(self.headers,
            Origin="https://live.bilibili.com",
            Referer="https://live.bilibili.com/")
        self.sessions = []
        self.csrfs = []
        self.rnd=int(time.time())
        if type(cookies)=="str":    cookies=[cookies]
        for i in range(len(cookies)):
            self.sessions.append(requests.session())
            self.csrfs.append("")
            self.update_cookie(cookies[i],i)
    
    def get_danmu_config(self,roomid,number=0,timeout=None):
        url="https://api.live.bilibili.com/xlive/web-room/v1/dM/GetDMConfigByGroup"
        params={"room_id":roomid}
        if timeout is None: timeout=self.timeout
        try:
            res=self.sessions[number].get(url=url,headers=self.headers,params=params,timeout=timeout)
            return json.loads(res.text)
        except Exception as e:  raise e
    
    def get_user_info(self,roomid,number=0,timeout=None):
        url="https://api.live.bilibili.com/xlive/web-room/v1/index/getInfoByUser"
        params={"room_id":roomid}
        if timeout is None: timeout=self.timeout
        try: 
            res=self.sessions[number].get(url=url,headers=self.headers,params=params,timeout=timeout)
            return json.loads(res.text)
        except Exception as e:  raise e
    
    def set_danmu_config(self,roomid,color=None,mode=None,number=0,timeout=None):
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
    
    def send_danmu(self,roomid,msg="",number=0,timeout=None):
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
    
    def update_cookie(self,cookie,number=0):
        requests.utils.add_dict_to_cookiejar(self.sessions[number].cookies,{"Cookie": cookie})
        so = re.search(r"bili_jct=([0-9a-f]+);?", cookie)
        self.csrfs[number]="" if so is None else so.group(1)

class NetEaseMusicAPI(BaseAPI):
    def __init__(self,timeout=5):
        super().__init__(timeout)

    def search_songs(self,keyword,limit=10,timeout=None,changeIP=False):
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
    
    def get_lyric(self,song_id,timeout=None,changeIP=False):
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
    
    def get_song_info(self,song_id,timeout=None,changeIP=False):
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
        super().__init__(timeout)
        self.headers = dict(self.headers,
            Referer="https://y.qq.com/portal/player.html")

    def search_songs(self,keyword,limit=10,timeout=None,changeIP=False):
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
    
    def get_lyric(self,song_mid,timeout=None,changeIP=False):
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
    
    def get_song_info(self,song_id,timeout=None,changeIP=False):
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
        super().__init__(timeout)

    def get_latest_bili_live_shield_words(self,timeout=None):
        url="https://cdn.jsdelivr.net/gh/FHChen0420/bili_live_shield_words@main/BiliLiveShieldWords.py"
        if timeout is None: timeout=self.timeout
        try:
            res=requests.get(url,headers=self.headers,timeout=timeout)
            return res.text
        except Exception as e:  raise e
