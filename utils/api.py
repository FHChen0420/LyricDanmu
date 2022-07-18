import json
import re
import time
from random import randint, random
from typing import List, Union

import requests


class BaseAPI:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.63 Safari/537.36 Edg/102.0.1245.30",
    }
    def __init__(self,timeout=(3.05,5)):
        self.timeout=timeout
        
    
    def set_default_timeout(self,timeout=(3.05,5)):
        self.timeout=timeout

class BiliLiveAPI(BaseAPI):
    def __init__(self,cookies:Union[List[str],str],timeout=(3.05,5)):
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
        res=requests.get(url=url,headers=self.headers,params=params,timeout=timeout)
        return json.loads(res.text)

    def get_danmu_config(self,roomid,number=0,timeout=None) -> dict:
        """获取用户在直播间内的可用弹幕颜色、弹幕位置等信息"""
        url="https://api.live.bilibili.com/xlive/web-room/v1/dM/GetDMConfigByGroup"
        params={"room_id":roomid}
        if timeout is None: timeout=self.timeout
        res=self.sessions[number].get(url=url,headers=self.headers,params=params,timeout=timeout)
        return json.loads(res.text)
    
    def get_user_info(self,roomid,number=0,timeout=None) -> dict:
        """获取用户在直播间内的当前弹幕颜色、弹幕位置、发言字数限制等信息"""
        url="https://api.live.bilibili.com/xlive/web-room/v1/index/getInfoByUser"
        params={"room_id":roomid}
        if timeout is None: timeout=self.timeout
        res=self.sessions[number].get(url=url,headers=self.headers,params=params,timeout=timeout)
        return json.loads(res.text)
    
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
        res=self.sessions[number].post(url=url,headers=self.headers,data=data,timeout=timeout)
        return json.loads(res.text)
    
    def send_danmu(self,roomid,msg,mode=1,number=0,timeout=None) -> dict:
        """向直播间发送弹幕"""
        url="https://api.live.bilibili.com/msg/send"
        data={
            "color": 16777215,
            "fontsize": 25,
            "mode": mode,
            "bubble": 0,
            "msg": msg,
            "roomid": roomid,
            "rnd": self.rnd,
            "csrf_token": self.csrfs[number],
            "csrf": self.csrfs[number],
        }
        if timeout is None: timeout=self.timeout
        res=self.sessions[number].post(url=url,headers=self.headers,data=data,timeout=timeout)
        return json.loads(res.text)
    
    def get_slient_user_list(self,roomid,number=0,timeout=None):
        """获取房间被禁言用户列表"""
        url="https://api.live.bilibili.com/xlive/web-ucenter/v1/banned/GetSilentUserList"
        params={
            "room_id": roomid,
            "ps": 1,
        }
        if timeout is None: timeout=self.timeout
        res=self.sessions[number].get(url=url,headers=self.headers,params=params,timeout=timeout)
        return json.loads(res.text)
    
    def add_slient_user(self,roomid,uid,number=0,timeout=None):
        """禁言用户"""
        url="https://api.live.bilibili.com/xlive/web-ucenter/v1/banned/AddSilentUser"
        data={
            "room_id": roomid,
            "tuid": uid,
            "mobile_app": "web",
            "csrf_token": self.csrfs[number],
            "csrf": self.csrfs[number],
        }
        if timeout is None: timeout=self.timeout
        res=self.sessions[number].post(url=url,headers=self.headers,data=data,timeout=timeout)
        return json.loads(res.text)

    def del_slient_user(self,roomid,silent_id,number=0,timeout=None):
        """解除用户禁言"""
        url="https://api.live.bilibili.com/banned_service/v1/Silent/del_room_block_user"
        data={
            "roomid": roomid,
            "id": silent_id,
            "csrf_token": self.csrfs[number],
            "csrf": self.csrfs[number],
        }
        if timeout is None: timeout=self.timeout
        res=self.sessions[number].post(url=url,headers=self.headers,data=data,timeout=timeout)
        return json.loads(res.text)
    
    def get_shield_keyword_list(self,roomid,number=0,timeout=None):
        """获取房间屏蔽词列表"""
        url="https://api.live.bilibili.com/xlive/web-ucenter/v1/banned/GetShieldKeywordList"
        params={
            "room_id": roomid,
            "ps": 2,
        }
        if timeout is None: timeout=self.timeout
        res=self.sessions[number].get(url=url,headers=self.headers,params=params,timeout=timeout)
        return json.loads(res.text)

    def add_shield_keyword(self,roomid,keyword,number=0,timeout=None):
        """添加房间屏蔽词"""
        url="https://api.live.bilibili.com/xlive/web-ucenter/v1/banned/AddShieldKeyword"
        data={
            "room_id": roomid,
            "keyword": keyword,
            "csrf_token": self.csrfs[number],
            "csrf": self.csrfs[number],
        }
        if timeout is None: timeout=self.timeout
        res=self.sessions[number].post(url=url,headers=self.headers,data=data,timeout=timeout)
        return json.loads(res.text)
    
    def del_shield_keyword(self,roomid,keyword,number=0,timeout=None):
        """删除房间屏蔽词"""
        url="https://api.live.bilibili.com/xlive/web-ucenter/v1/banned/DelShieldKeyword"
        data={
            "room_id": roomid,
            "keyword": keyword,
            "csrf_token": self.csrfs[number],
            "csrf": self.csrfs[number],
        }
        if timeout is None: timeout=self.timeout
        res=self.sessions[number].post(url=url,headers=self.headers,data=data,timeout=timeout)
        return json.loads(res.text)
    
    def search_live_users(self,keyword,page_size=10,timeout=None) -> dict:
        """根据关键字搜索直播用户"""
        url="https://api.bilibili.com/x/web-interface/search/type"
        params={
            "keyword": keyword,
            "search_type": "live_user",
            "page_size": page_size,
        }
        if timeout is None: timeout=self.timeout
        res=requests.get(url=url,headers=self.headers,params=params,timeout=timeout)
        return json.loads(res.text)
    
    def get_login_url(self,timeout=None):
        """获取登录链接"""
        url="https://passport.bilibili.com/qrcode/getLoginUrl"
        if timeout is None: timeout=self.timeout
        res=requests.get(url=url,headers=self.headers,timeout=timeout)
        return json.loads(res.text)
    
    def get_login_info(self,oauthKey,timeout=None):
        """检查登录链接状态，获取登录信息"""
        url="https://passport.bilibili.com/qrcode/getLoginInfo"
        data={
            "oauthKey": oauthKey,
        }
        if timeout is None: timeout=self.timeout
        res=requests.post(url=url,headers=self.headers,data=data,timeout=timeout)
        return json.loads(res.text)
    
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
    CN_IP=( "110.42", "222.206", "220.180", "180.163", "113.100", #北京 山东 福建 上海 广东
            "125.83", "183.140", "49.78",   "106.230", "223.150") #重庆 浙江 江苏 江西 湖南

    def __init__(self,timeout=(3.05,5)):
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
        res=requests.get(url=url,headers=headers,params=params,timeout=timeout)
        return json.loads(res.text)
    
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
        res=requests.get(url=url,headers=headers,params=params,timeout=timeout)
        return json.loads(res.text)
    
    def get_song_info(self,song_id,timeout=None,changeIP=False) -> dict:
        """根据歌曲ID获取歌曲信息"""
        url="https://music.163.com/api/song/detail"
        params= {
            "id": song_id,
            "ids": "[%s]"%str(song_id),
        }
        if timeout is None: timeout=self.timeout
        headers=self.attach_cn_ip(self.headers) if changeIP else self.headers
        res=requests.get(url=url,headers=headers,params=params,timeout=timeout)
        return json.loads(res.text)
    
    def attach_cn_ip(self,headers:dict) -> dict:
        new_headers= dict(headers)
        ip=self.CN_IP[randint(0,len(self.CN_IP)-1)]+"."+str(randint(10,250))+"."+str(randint(10,250))
        new_headers["X-Real-IP"]=ip
        return new_headers
    
class QQMusicAPI(BaseAPI):
    def __init__(self,cookie,timeout=(3.05,5)):
        """QQ音乐API"""
        super().__init__(timeout)
        self.headers = dict(BaseAPI.headers,
            Referer="https://y.qq.com/",
            Origin="https://y.qq.com")
        self.headers_login = dict(BaseAPI.headers,
            Host="ssl.ptlogin2.qq.com",
            Referer="https://xui.ptlogin2.qq.com/")
        self.__session=requests.session()
        self.set_cookie(cookie)
        self.__ptqrtoken=""
        self.__login_sig=""

    def __get_token(self, string, offset=5381):
        """加密函数，用于计算g_tk等值"""
        e = offset
        for c in string:
            e += (e << 5) + ord(c)
        return 0x7fffffff & e
    
    # def __get_uuid(self):
    #     """生成uuid并保存到cookie中(非必需)"""
    #     def _replace(x):
    #         i = randint(0,15)
    #         i = i | 0 if x.group()=="x" else i & 0x3 | 0x8
    #         return "0123456789abcdef"[i]
    #     template = "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx"
    #     uuid = re.sub("[xy]",_replace,template).upper()
    #     self.__session.cookies.set("ui",uuid,domain=".graph.qq.com",path="/")
    #     return uuid

    def _xlogin(self):
        """获取pt_login_sig"""
        url="https://xui.ptlogin2.qq.com/cgi-bin/xlogin"
        params={
            "appid": 716027609,
            "daid": 383,
            "style": 33,
            "login_text": "登录",
            "hide_title_bar": 1,
            "hide_border": 1,
            "target": "self",
            "s_url": "https://graph.qq.com/oauth2.0/login_jump",
            "pt_3rd_aid": 100497308,
            "pt_feedback_link": "https://support.qq.com/products/77942?customInfo=.appid100497308",
            "theme": 2,
            "verify_theme": "",
        }
        self.__session.get(url=url,params=params,timeout=(3.05,5))
        self.__login_sig=self.__session.cookies.get("pt_login_sig")
    
    def get_login_qrcode(self):
        """获取登录二维码"""
        url="https://ssl.ptlogin2.qq.com/ptqrshow"
        params= {
            "appid": 716027609,
            "e": 2,
            "l": "M",
            "s": 3,
            "d": 72,
            "v": 4,
            "t": random(),
            "daid": 383,
            "pt_3rd_aid": 100497308,
        }
        res=self.__session.get(url=url,headers=self.headers_login,params=params,timeout=(3.05,5))
        qrsig=self.__session.cookies.get("qrsig")
        self.__ptqrtoken=self.__get_token(qrsig, 0)
        return res
    
    def get_login_info(self):
        """查询扫码登录状态"""
        url="https://ssl.ptlogin2.qq.com/ptqrlogin"
        params={
            "u1": "https://graph.qq.com/oauth2.0/login_jump",
            "ptqrtoken": self.__ptqrtoken,
            "ptredirect": 0,
            "h": 1,
            "t": 1,
            "g": 1,
            "from_ui": 1,
            "ptlang": 2052,
            "action": "0-0-%d"%int(time.time()*1000),
            "js_ver": 22071217,
            "js_type": 1,
            "login_sig": self.__login_sig,
            "pt_uistyle": 40,
            "aid": 716027609,
            "daid": 383,
            "pt_3rd_aid": 100497308,
            "has_onekey": 1,
            "o1vId": "f49360ebaddf6358d888317a4e8aa604",
        }
        res=self.__session.get(url=url,headers=self.headers_login,params=params,timeout=(3.05,5))
        return res
    
    def authorize(self,check_sig_url):
        """扫码并确认后，调用此函数获取完整cookie"""
        self.__session.get(url=check_sig_url,timeout=(3.05,5))
        p_skey=self.__session.cookies.get("p_skey")
        auth_url="https://graph.qq.com/oauth2.0/authorize"
        auth_data={
            "response_type": "code",
            "client_id": 100497308,
            "redirect_uri": "https://y.qq.com/portal/wx_redirect.html?login_type=1&surl=https://y.qq.com/",
            "scope": "all",
            "state": "state",
            "switch": "",
            "from_ptlogin": 1,
            "src": 1,
            "update_auth": 1,
            "openapi": "80901010_1030",
            "g_tk": self.__get_token(p_skey),
            "auth_time": int(time.time()*1000),
            "ui": "", # self.__get_uuid(),
        }
        auth_res=self.__session.post(url=auth_url,data=auth_data,timeout=(3.05,5))
        location=auth_res.history[0].headers["location"]
        code=re.search("code=([0-9A-F]+)",location).group(1)
        login_srv_url="https://u.y.qq.com/cgi-bin/musicu.fcg"
        login_srv_json_data={
            "comm": {
                "g_tk": 5381,
                "platform": "yqq",
                "ct": 24,
                "cv": 0
            },
            "req": {
                "module": "QQConnectLogin.LoginServer",
                "method": "QQLogin",
                "param": {
                    "code": code
                }
            }
        }
        self.__session.post(url=login_srv_url,headers=self.headers,json=login_srv_json_data,timeout=(3.05,5))
        
    def search_songs(self,keyword,limit=10,timeout=None) -> dict:
        """按关键字搜索歌曲"""
        url="https://u.y.qq.com/cgi-bin/musicu.fcg"
        json_data = {
            "comm": {
                "cv": 4747474,
                "ct": 24,
                "format": "json",
                "inCharset": "utf-8",
                "outCharset": "utf-8",
                "notice": 0,
                "platform": "yqq.json",
                "needNewCode": 1,
                "uin": 0,
                "g_tk_new_20200303": 1244134330, #任意
                "g_tk": 1244134330 #任意
            },
            "req_1": {
                "method": "DoSearchForQQMusicDesktop",
                "module": "music.search.SearchCgiService",
                "param": {
                    "remoteplace": "txt.yqq.top",
                    "searchid": "",
                    "search_type": 0,
                    "query": keyword.encode("utf-8").decode('unicode_escape'),
                    "page_num": 1,
                    "num_per_page": limit
                }
            }
        }
        if timeout is None: timeout=self.timeout
        res=self.__session.post(url=url,headers=self.headers,json=json_data,timeout=timeout)
        return json.loads(res.text)
    
    def get_lyric(self,song_mid,timeout=None) -> dict:
        """根据歌曲MID获取歌词"""
        url="https://c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric_new.fcg"
        params= {
            "songmid": song_mid,
            "nobase64": 1,
            "g_tk": 5381,
            "format": "json",
        }
        if timeout is None: timeout=self.timeout
        res=requests.get(url=url,headers=self.headers,params=params,timeout=timeout)
        return json.loads(res.text)
    
    def get_song_info(self,song_id,timeout=None) -> dict:
        """根据歌曲ID获取歌曲信息"""
        url="https://c.y.qq.com/v8/fcg-bin/fcg_play_single_song.fcg"
        params= {
            "songid": song_id,
            "format": "json",
        }
        if timeout is None: timeout=self.timeout
        res=requests.get(url=url,headers=self.headers,params=params,timeout=timeout)
        return json.loads(res.text)
    
    def get_cookie(self):
        uin = self.__session.cookies.get("uin",domain=".qq.com")
        qm_keyst = self.__session.cookies.get("qm_keyst",domain=".qq.com")
        return f"uin={uin if uin else ''};qm_keyst={qm_keyst if qm_keyst else ''}"
    
    def set_cookie(self,cookie:str):
        cookie = re.sub(r"\s+", "", cookie)
        mo1 = re.search(r"uin=([^;]+)", cookie)
        mo2 = re.search(r"qm_keyst=([^;]+)", cookie)
        if mo1: self.__session.cookies.set("uin",mo1.group(1),domain=".qq.com")
        if mo2: self.__session.cookies.set("qm_keyst",mo2.group(1),domain=".qq.com")

class JsdelivrAPI(BaseAPI):
    def __init__(self, timeout=(6.05,5)):
        """Jsdelivr公共CDN的API"""
        super().__init__(timeout)

    def get_latest_bili_live_shield_words(self,domain="cdn",timeout=None) -> str:
        """获取最新的B站直播屏蔽词处理脚本（Github项目：FHChen0420/bili_live_shield_words）"""
        url=f"https://{domain}.jsdelivr.net/gh/FHChen0420/bili_live_shield_words@main/BiliLiveShieldWords.py"
        if timeout is None: timeout=self.timeout
        res=requests.get(url,headers=self.headers,timeout=timeout)
        return res.text
