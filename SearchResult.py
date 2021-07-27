import wx
import re
import requests
import json
import pyperclip
import xml.dom.minidom
from math import ceil
from random import randint
from pubsub import pub
from langconv import Converter
from MarkSettingFrame import MarkSettingFrame
from util import UIChange,SetFont,getNodeValue
from other_data import preprocess_cn_rules,ignore_lyric_pattern

class SearchResult(wx.Frame):
    def __init__(self, parent, src, words, mark_ids, local_names):
        #IP段
        self.ips=[
            "110.42", # 北京 110.42.0.0 - 110.42.255.255
            "222.206", #山东
            "220.180", #福建1
            "180.163", #上海
            "113.100", #广东
            "120.36", #福建2
            "183.140", #浙江
            "49.78", #江苏
            "106.230", #江西
            "223.150", #湖南
        ]
        # 请求参数
        self.url_GetSongsWY = "https://music.163.com/api/search/get/web"
        self.url_GetLyricWY = "https://music.163.com/api/song/lyric"
        self.url_GetSongInfoWY = "https://music.163.com/api/song/detail"
        self.headersWY = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.221 Safari/537.36 SE 2.X MetaSr 1.0",
        }
        self.params_GetSongsWY = {
            "s": "",  # 查询关键字
            "limit": parent.search_num,  # 结果条数
            "type": 1,
        }
        self.params_GetLyricWY = {
            "id": 0,  # 歌曲id
            "lv": -1,
            "tv": -1,
            # "kv":-1,
            # "os": "pc",
        }
        self.params_GetSongInfoWY = {
            "id": 0,  # 歌曲id
            "ids": "[]",  # [歌曲id]
        }
        self.url_GetSongsQQ = "https://c.y.qq.com/soso/fcgi-bin/client_search_cp"
        self.url_GetLyricQQ = "https://c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric_new.fcg"
        self.url_GetSongInfoQQ = "https://c.y.qq.com/v8/fcg-bin/fcg_play_single_song.fcg"
        self.headersQQ = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.221 Safari/537.36 SE 2.X MetaSr 1.0",
            "Referer": "https://y.qq.com/portal/player.html",
        }
        self.params_GetSongsQQ = {
            "w": "",  # 查询关键字
            "n": parent.search_num,  # 结果条数
            "format": "json",
        }
        self.params_GetLyricQQ = {
            "songmid": "",  # 歌曲mid
            "nobase64": 1,
            "g_tk": 5381,
            "format": "json",
        }
        self.params_GetSongInfoQQ = {
            "songid": 0,  # 歌曲id
            "format": "json",
        }
        # 配置
        self.page_limit = parent.page_limit
        # 运行
        self.parent = parent
        self.src=src
        self.show_pin=parent.show_pin
        self.all_songs = []
        self.ip_idx=0
        self.GetLocalSongs(local_names)
        self.GetMarkSongs(mark_ids)
        if src=="wy":
            self.GetNetworkSongsWY(words, mark_ids)
        else:
            self.GetNetworkSongsQQ(words, mark_ids)

    def ChangeIP(self):
        self.ip_idx=0 if self.ip_idx+1>=len(self.ips) else self.ip_idx+1
        ip=self.ips[self.ip_idx]+"."+str(randint(10,250))+"."+str(randint(10,250))
        self.headersWY["X-Real-IP"]=ip
        self.headersQQ["X-Real-IP"]=ip

    def GetLocalSongs(self,local_names):
        if len(local_names) == 0:
            return
        for file in local_names:
            info_raw = self.parent.locals[file]
            info=info_raw.split(";",4)
            song = {}
            song["my_local"] = True
            song["id"] = file
            song["name"] = info[0]
            song["artists"] = [{"name":info[1]}]
            song["album"]= {"name":"本地歌词"}
            song["type"] = info[2]
            song["tags"] = info[3]
            self.all_songs.append(song)

    def GetMarkSongs(self,mark_ids):
        if len(mark_ids) == 0:
            return True
        for mid in mark_ids:
            self.ChangeIP()
            src,song_id=mid[0],mid[1:]
            try:
                if src=="W":
                    self.params_GetSongInfoWY["id"] = song_id
                    self.params_GetSongInfoWY["ids"] = "[" + song_id + "]"
                    res = requests.get(url=self.url_GetSongInfoWY, headers=self.headersWY, params=self.params_GetSongInfoWY,timeout=(5, 5))
                else:
                    self.params_GetSongInfoQQ["songid"] = song_id
                    res = requests.get(url=self.url_GetSongInfoQQ, headers=self.headersQQ, params=self.params_GetSongInfoQQ,timeout=(5, 5))
                info = json.loads(res.text)
                if info["code"] == (200 if src=="W" else 0):
                    if len(info["songs" if src=="W" else "data"])==0:
                        song={}
                        song["my_mark"] = True
                        song["id"] = song_id
                        song["name"] = "[歌曲已失效，请删除收藏] [id:%s]"%song_id
                        song["alias"] = []
                        song["artists"] = [{"name":"?"}]
                        song["album"] = {"name":"?"}
                        song["my_mark"] = True
                        self.all_songs.append(song)
                    elif src=="W":
                        info["songs"][0]["my_mark"] = True
                        info["songs"][0]["id"]=str(info["songs"][0]["id"])
                        self.all_songs += info["songs"]
                    elif src=="Q":
                        qq_song = info["data"][0]
                        song={}
                        song["my_mark"] = True
                        song["id"] = song_id+";"+qq_song["mid"]
                        song["name"] = qq_song["name"]
                        song["alias"] = []
                        if qq_song["subtitle"] is not None and qq_song["subtitle"].strip()!="":
                            song["alias"].append(qq_song["subtitle"])
                        song["artists"] = qq_song["singer"]
                        song["album"] = qq_song["album"]
                        song["my_mark"] = True
                        self.all_songs.append(song)
                else:
                    raise Exception("Code: "+str(info["code"]))
            except Exception as e:
                print("GetMarkSongs:")
                print(e)
                song={}
                song["my_mark"] = True
                song["id"] = song_id
                song["name"] = "[获取失败，请重试]"
                song["alias"] = []
                song["artists"] = [{"name":"?"}]
                song["album"] = {"name":"?"}
                self.all_songs.append(song)

    def GetNetworkSongsWY(self, words, mark_ids):
        try:
            self.ChangeIP()
            self.params_GetSongsWY["s"] = words
            res = requests.get(url=self.url_GetSongsWY, headers=self.headersWY, params=self.params_GetSongsWY,timeout=(5, 5))
            songs_result = json.loads(res.text)
            if songs_result["code"] == 200:
                if "abroad" in songs_result.keys():
                    dlg = wx.MessageDialog(None, "轮换IP出错，请反馈给作者", "搜索出错", wx.OK)
                    dlg.ShowModal()
                    dlg.Destroy()
                    return
                elif "songs" not in songs_result["result"] and len(self.all_songs)==0:
                    dlg = wx.MessageDialog(None, "找不到相关歌曲", "提示", wx.OK)
                    dlg.ShowModal()
                    dlg.Destroy()
                    return
                self.recommond = songs_result["result"]["queryCorrected"][0] if "queryCorrected" in songs_result[
                    "result"].keys() else None
                songs=songs_result["result"]["songs"]
                for song in songs:
                    if "W"+str(song["id"]) in mark_ids: continue
                    song["id"]=str(song["id"])
                    self.all_songs.append(song)
                self.ShowFrame(self.parent)
            else:
                dlg = wx.MessageDialog(None, "获取歌曲列表失败", "搜索出错", wx.OK)
                dlg.ShowModal()
                dlg.Destroy()
        except requests.exceptions.ConnectionError as e:
            print(e)
            dlg = wx.MessageDialog(None, "网络异常，请重试", "搜索出错", wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
        except requests.exceptions.ReadTimeout:
            dlg = wx.MessageDialog(None, "获取超时，请重试", "搜索出错", wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
        except Exception as e:
            print("GetNetworkSongsWY:")
            print(e)

    def GetNetworkSongsQQ(self, words, mark_ids):
        try:
            self.ChangeIP()
            self.params_GetSongsQQ["w"] = words
            res = requests.get(url=self.url_GetSongsQQ, headers=self.headersQQ, params=self.params_GetSongsQQ, timeout=(5, 5))
            songs_result = json.loads(res.text)
            if songs_result["code"] == 0:
                if songs_result["subcode"]!=0 and len(self.all_songs)==0:
                    dlg = wx.MessageDialog(None, "找不到相关歌曲", "提示", wx.OK)
                    dlg.ShowModal()
                    dlg.Destroy()
                    return
                self.recommond = None
                qq_songs=songs_result["data"]["song"]["list"]
                for qq_song in qq_songs:
                    song={}
                    if "Q%d"%qq_song["songid"] in mark_ids:  continue
                    song["id"]="%d;%s"%(qq_song["songid"],qq_song["songmid"]) #id;mid
                    song["name"]=qq_song["songname"]
                    song["artists"]=[{"name": x["name"]} for x in qq_song["singer"]]
                    song["alias"] = []
                    song["album"]={"name": qq_song["albumname"]}
                    self.all_songs.append(song)
                self.ShowFrame(self.parent)
            else:
                dlg = wx.MessageDialog(None, "获取歌曲列表失败", "搜索出错", wx.OK)
                dlg.ShowModal()
                dlg.Destroy()
        except requests.exceptions.ConnectionError:
            dlg = wx.MessageDialog(None, "网络异常，请重试", "搜索出错", wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
        except requests.exceptions.ReadTimeout:
            dlg = wx.MessageDialog(None, "获取超时，请重试", "搜索出错", wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
        except Exception as e:
            print("GetNetworkSongsQQ:")
            print(e)

    def ShowFrame(self, parent):
        # 窗体
        title="搜索结果 - "+("网易云" if self.src=="wy" else "QQ音乐")
        wx.Frame.__init__(self, parent, title=title, size=(520, self.page_limit * 50 + 120),
                          style=wx.DEFAULT_FRAME_STYLE ^ (wx.RESIZE_BORDER | wx.MAXIMIZE_BOX))
        if self.show_pin:
            self.ToggleWindowStyle(wx.STAY_ON_TOP)
        self.markSettingFrame=None
        self.p0 = wx.Panel(self, -1, pos=(0, 0), size=(520, 80))
        wins=parent.platform=="win"
        # 内容
        if self.recommond:
            txtRecommond = wx.StaticText(self.p0, -1, "建议：" + self.recommond, pos=(15, 10))
            SetFont(txtRecommond,11 if wins else 15,bold=True)
            btnCopyRecommond = wx.Button(self.p0, -1, "复制\n建议", pos=(330, 10), size=(40, 40))
            btnCopyRecommond.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)  #
            btnCopyRecommond.Bind(wx.EVT_BUTTON, self.CopyRecommond)
        self.txtMsg = wx.StaticText(self.p0, -1, "", pos=(50, 40), size=(280, -1), style=wx.ALIGN_CENTER)
        SetFont(self.txtMsg,13 if wins else 17,bold=True,name="微软雅黑" if wins else None)
        txtGetLyric = wx.StaticText(self.p0, -1, "歌词", pos=(387, 60))
        txtCopyName = wx.StaticText(self.p0, -1, "歌名", pos=(426, 60))
        txtMark = wx.StaticText(self.p0, -1, "收藏", pos=(465, 60))
        self.btnPrevPage = wx.Button(self.p0, -1, "◁", pos=(380, 10), size=(40, 40))
        self.btnPageNum = wx.Button(self.p0, -1, "", pos=(419, 10), size=(40, 40))
        self.btnNextPage = wx.Button(self.p0, -1, "▷", pos=(458, 10), size=(40, 40))
        SetFont(self.btnPrevPage,14)
        SetFont(self.btnNextPage,14)
        self.btnPrevPage.Bind(wx.EVT_BUTTON, self.PrevPage)
        self.btnNextPage.Bind(wx.EVT_BUTTON, self.NextPage)
        self.btnPrevPage.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)  #
        self.btnNextPage.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)  #
        song_num = len(self.all_songs)
        self.page_num = int(ceil(song_num * 1.0 / self.page_limit))
        self.panels = []
        self.txtTypes=[]
        for i in range(self.page_num):
            p = wx.Panel(self, -1, pos=(0, 80), size=(520, 520))
            p.Show(False)
            self.panels.append(p)
            self.txtTypes.append([])
            j = 0
            for song in self.all_songs[i * self.page_limit:(i + 1) * self.page_limit]:
                song_id=str(song["id"])
                short_name=re.sub("\(.*?\)|（.*?）","",song["name"])
                txtName = wx.StaticText(p, -1, song["name"].strip(), pos=(15, 50 * j), size=(360, 30),style=wx.ST_NO_AUTORESIZE)
                txtType = wx.StaticText(self.panels[i], -1, "", pos=(15, 50 * j + 25), size=(35, -1),style=wx.ST_NO_AUTORESIZE)
                txtArtist = wx.StaticText(p, -1, song["artists"][0]["name"].strip(), pos=(50, 50 * j + 25),size=(100, -1), style=wx.ST_NO_AUTORESIZE)
                txtAlbum = wx.StaticText(p, -1, song["album"]["name"].strip(), pos=(155, 50 * j + 25), size=(220, -1),style=wx.ST_NO_AUTORESIZE)
                SetFont(txtName,12 if wins else 16,bold=True,name="微软雅黑" if wins else None)
                btn1 = wx.Button(p, -1, "▶", pos=(380, 50 * j), size=(40, 40), name=song_id+";"+short_name)
                btn2 = wx.Button(p, -1, "✎", pos=(419, 50 * j), size=(40, 40), name=song["name"])
                btn3 = wx.Button(p, -1, "☆", pos=(458, 50 * j), size=(40, 40), name=song_id)
                SetFont(btn1,14)
                SetFont(btn2,14)
                SetFont(btn3,14)
                btn2.Bind(wx.EVT_BUTTON, self.CopyName)
                btn1.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)  #
                btn2.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)  #
                btn3.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)  #
                if i == 0 and j == 0:
                    btn1.SetFocus()
                if "my_local" in song.keys():
                    txtName.SetForegroundColour("MEDIUM BLUE")
                    btn3.SetLabel("✪")
                    btn1.SetName(song_id)
                    btn1.Bind(wx.EVT_BUTTON, self.GetLocalLyric)
                    btn3.Bind(wx.EVT_BUTTON, self.ShowLocalInfo)
                    if song["type"]=="双语":
                        txtType.SetForegroundColour("blue")
                        txtType.SetLabel("双语")
                    else:
                        txtType.SetForegroundColour("purple")
                        txtType.SetLabel("单语")
                    self.txtTypes[i].append(txtType)
                    j+=1
                    continue
                elif "my_mark" in song.keys():
                    txtName.SetForegroundColour("MEDIUM BLUE")
                    btn3.SetLabel("★")
                self.txtTypes[i].append(txtType)
                if ";" not in song_id:
                    btn1.Bind(wx.EVT_BUTTON, self.GetNetworkLyricWY)
                    btn3.Bind(wx.EVT_BUTTON, self.OnMarkWY)
                else:
                    btn1.Bind(wx.EVT_BUTTON, self.GetNetworkLyricQQ)
                    btn3.Bind(wx.EVT_BUTTON, self.OnMarkQQ)
                j+=1
        self.parent.pool.submit(self.ThreadOfGetLyricType)
        self.cur_page = 0
        self.btnPageNum.Disable()
        self.btnPageNum.SetLabel("1/%d"%self.page_num)
        self.panels[0].Show(True)
        self.Show(True)

    def ThreadOfGetLyricType(self):
        for i in range(self.page_num):
            j=0
            for song in self.all_songs[i * self.page_limit:(i + 1) * self.page_limit]:
                if "my_local" in song.keys():
                    j+=1
                    continue
                txt=self.txtTypes[i][j]
                if ";" not in song["id"]:
                    self.GetLyricTypeWY(song["id"],txt)
                else:
                    self.GetLyricTypeQQ(song["id"],txt)
                j+=1

    def GetLyricTypeWY(self, song_id, txt):
        try:
            self.ChangeIP()
            self.params_GetLyricWY["id"] = song_id
            res = requests.get(url=self.url_GetLyricWY, headers=self.headersWY, params=self.params_GetLyricWY, timeout=(5, 5))
            lyrics = json.loads(res.text)
            if lyrics["code"] != 200:
                UIChange(obj=txt,color="gray",label="错误")
                return
            if "lrc" not in lyrics.keys():
                UIChange(obj=txt,color="red",label="无词")
                return
            lrcO = lyrics["lrc"]["lyric"]
            if lrcO is None or lrcO.strip() == "":
                UIChange(obj=txt,color="red",label="无词")
                return
            if re.search(r"\[\d+:\d+(\.\d*)?\]", lrcO) is None:
                UIChange(obj=txt,color="SEA GREEN",label="无轴")
                return
            line_num = 0
            listO = lrcO.strip().split("\n")
            for o in listO:
                parts=o.split("]")
                content=parts[-1].strip()
                if content not in ["","<END>"] and not re.match(ignore_lyric_pattern,content):
                    line_num += len(parts)-1
            if lyrics["tlyric"]["lyric"].strip() == "":
                UIChange(obj=txt,color="purple",label="单%d"%line_num)
                return
            UIChange(obj=txt,color="blue",label="双%d"%line_num)
        except RuntimeError:
            pass
        except:
            try:
                UIChange(obj=txt,color="gray",label="重试")
            except RuntimeError:
                pass

    def GetLyricTypeQQ(self, song_id,txt):
        try:
            self.ChangeIP()
            self.params_GetLyricQQ["songmid"] = song_id.split(";")[1]
            res = requests.get(url=self.url_GetLyricQQ, headers=self.headersQQ, params=self.params_GetLyricQQ, timeout=(5, 5))
            lyrics = json.loads(res.text)
            if lyrics["code"] == -1901:
                UIChange(obj=txt,color="red",label="无词")
                return
            if lyrics["code"] != 0:
                UIChange(obj=txt,color="gray",label="错误")
                return
            lrcO = lyrics["lyric"].strip()
            if lrcO == "[00:00:00]此歌曲为没有填词的纯音乐，请您欣赏":
                UIChange(obj=txt,color="red",label="无词")
                return
            if re.search(r"\[\d+:\d+(\.\d*)?\]", lrcO) is None:
                UIChange(obj=txt,color="SEA GREEN",label="无轴")
                return
            line_num = 0
            listO = lrcO.strip().split("\n")
            for o in listO:
                parts=o.split("]")
                content=parts[-1].strip()
                if content not in ["","<END>"] and not re.match(ignore_lyric_pattern,content):
                    line_num += len(parts)-1
            if lyrics["trans"].strip() == "":
                UIChange(obj=txt,color="purple",label="单%d"%line_num)
                return
            UIChange(obj=txt,color="blue",label="双%d"%line_num)
        except RuntimeError:
            pass
        except:
            try:
                UIChange(obj=txt,color="gray",label="重试")
            except RuntimeError:
                pass

    def GetLocalLyric(self,event):
        self.txtMsg.SetForegroundColour("gray")
        self.txtMsg.SetLabel("获取歌词中...")
        file=event.GetEventObject().GetName()
        try:
            localSong = xml.dom.minidom.parse("songs/"+file).documentElement
            has_trans=getNodeValue(localSong,"type")=="双语"
            data={
                "src": "local",
                "has_trans": has_trans,
                "lyric": getNodeValue(localSong,"lyric"),
                "name": re.sub("\(.*?\)|（.*?）","",getNodeValue(localSong,"name")),
            }
            self.parent.RecvLyric(data)
            if has_trans:
                self.txtMsg.SetForegroundColour("blue")
                self.txtMsg.SetLabel("已获取双语歌词")
            else:
                self.txtMsg.SetForegroundColour("purple")
                self.txtMsg.SetLabel("已获取单语歌词")
        except:
            self.txtMsg.SetForegroundColour("red")
            self.txtMsg.SetLabel("读取本地文件失败")

    def ShowLocalInfo(self,event):
        file = event.GetEventObject().GetName()
        if not self.parent.ShowLocalInfo(file):
            dlg = wx.MessageDialog(None, "读取本地文件失败", "获取信息出错", wx.OK)
            dlg.ShowModal()
            dlg.Destroy()

    def GetNetworkLyricWY(self, event):
        try:
            self.ChangeIP()
            self.txtMsg.SetForegroundColour("gray")
            self.txtMsg.SetLabel("获取歌词中...")
            info=event.GetEventObject().GetName().split(";",1)
            self.params_GetLyricWY["id"],name = info[0],info[1]
            res = requests.get(url=self.url_GetLyricWY, headers=self.headersWY, params=self.params_GetLyricWY, timeout=(5, 5))
            lyrics = json.loads(res.text)
            if lyrics["code"] != 200:
                self.txtMsg.SetForegroundColour("red")
                self.txtMsg.SetLabel("获取歌词失败")
                return
            if "lrc" not in lyrics.keys():
                self.txtMsg.SetForegroundColour("red")
                self.txtMsg.SetLabel("目标歌曲无歌词")
                return
            lrcO = lyrics["lrc"]["lyric"]
            lrcT = self.PreprocessCN(lyrics["tlyric"]["lyric"])
            if lrcO is None or lrcO.strip() == "":
                self.txtMsg.SetForegroundColour("red")
                self.txtMsg.SetLabel("目标歌曲无歌词")
                return
            if re.search(r"\[\d+:\d+(\.\d*)?\]", lrcO) is None:
                lrcO = lrcO.strip()
                dlg = wx.MessageDialog(None, "是否以双语形式获取歌词？", "提示", wx.YES_NO|wx.NO_DEFAULT)
                has_trans = dlg.ShowModal() == wx.ID_YES
                data={
                    "src": "wy",
                    "has_trans": has_trans,
                    "lyric": lrcO,
                    "name": name,
                }
                self.parent.RecvLyric(data)
                dlg.Destroy()
                if has_trans:
                    self.txtMsg.SetForegroundColour("blue")
                    self.txtMsg.SetLabel("已获取双语歌词")
                else:
                    self.txtMsg.SetForegroundColour("purple")
                    self.txtMsg.SetLabel("已获取单语歌词")
            elif lrcT.strip() == "":
                data={
                    "src": "wy",
                    "has_trans": False,
                    "lyric": lrcO,
                    "name": name,
                }
                self.parent.RecvLyric(data)
                self.txtMsg.SetForegroundColour("purple")
                self.txtMsg.SetLabel("已获取单语歌词")
            else:
                data={
                    "src": "wy",
                    "has_trans": True,
                    "lyric": lrcO,
                    "tlyric": lrcT,
                    "name": name,
                }
                self.parent.RecvLyric(data)
                self.txtMsg.SetForegroundColour("blue")
                self.txtMsg.SetLabel("已获取双语歌词")
        except requests.exceptions.ConnectionError:
            self.txtMsg.SetLabel("网络异常，请重试")
            dlg = wx.MessageDialog(None, "网络异常，请重试", "获取歌词出错", wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
        except requests.exceptions.ReadTimeout:
            self.txtMsg.SetLabel("获取超时，请重试")
            dlg = wx.MessageDialog(None, "获取超时，请重试", "获取歌词出错", wx.OK)
            dlg.ShowModal()
            dlg.Destroy()

    def GetNetworkLyricQQ(self, event):
        try:
            self.ChangeIP()
            self.txtMsg.SetForegroundColour("gray")
            self.txtMsg.SetLabel("获取歌词中...")
            info=event.GetEventObject().GetName().split(";",2)
            self.params_GetLyricQQ["songmid"],name = info[1],info[2]
            res = requests.get(url=self.url_GetLyricQQ, headers=self.headersQQ, params=self.params_GetLyricQQ, timeout=(5, 5))
            lyrics = json.loads(res.text)
            if lyrics["code"] == -1901:
                self.txtMsg.SetForegroundColour("red")
                self.txtMsg.SetLabel("目标歌曲无歌词")
                return
            if lyrics["code"] != 0:
                self.txtMsg.SetForegroundColour("red")
                self.txtMsg.SetLabel("获取歌词失败")
                return
            lrcO = lyrics["lyric"]
            lrcT = self.PreprocessCN(lyrics["trans"])
            if lrcO.strip() == "[00:00:00]此歌曲为没有填词的纯音乐，请您欣赏":
                self.txtMsg.SetForegroundColour("red")
                self.txtMsg.SetLabel("目标歌曲无歌词")
                return
            if re.search(r"\[\d+:\d+(\.\d*)?\]", lrcO) is None:
                lrcO = lrcO.strip()
                dlg = wx.MessageDialog(None, "是否以双语形式获取歌词？", "提示", wx.YES_NO|wx.NO_DEFAULT)
                has_trans = dlg.ShowModal() == wx.ID_YES
                data={
                    "src": "qq",
                    "has_trans": has_trans,
                    "lyric": lrcO,
                    "name": name,
                }
                self.parent.RecvLyric(data)
                dlg.Destroy()
                if has_trans:
                    self.txtMsg.SetForegroundColour("blue")
                    self.txtMsg.SetLabel("已获取双语歌词")
                else:
                    self.txtMsg.SetForegroundColour("purple")
                    self.txtMsg.SetLabel("已获取单语歌词")
            elif lrcT.strip() == "":
                data={
                    "src": "qq",
                    "has_trans": False,
                    "lyric": lrcO,
                    "name": name,
                }
                self.parent.RecvLyric(data)
                self.txtMsg.SetForegroundColour("purple")
                self.txtMsg.SetLabel("已获取单语歌词")
            else:
                data={
                    "src": "qq",
                    "has_trans": True,
                    "lyric": lrcO,
                    "tlyric": lrcT,
                    "name": name,
                }
                self.parent.RecvLyric(data)
                self.txtMsg.SetForegroundColour("blue")
                self.txtMsg.SetLabel("已获取双语歌词")
        except requests.exceptions.ConnectionError:
            self.txtMsg.SetLabel("网络异常，请重试")
            dlg = wx.MessageDialog(None, "网络异常，请重试", "获取歌词出错", wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
        except requests.exceptions.ReadTimeout:
            self.txtMsg.SetLabel("获取超时，请重试")
            dlg = wx.MessageDialog(None, "获取超时，请重试", "获取歌词出错", wx.OK)
            dlg.ShowModal()
            dlg.Destroy()

    def PrevPage(self, event):
        if self.cur_page > 0:
            self.panels[self.cur_page - 1].Show(True)
            self.panels[self.cur_page].Show(False)
            self.cur_page -= 1
            self.btnPageNum.SetLabel("%d/%d" % (self.cur_page+1, self.page_num))

    def NextPage(self, event):
        if self.cur_page + 1 < self.page_num:
            self.panels[self.cur_page + 1].Show(True)
            self.panels[self.cur_page].Show(False)
            self.cur_page += 1
            self.btnPageNum.SetLabel("%d/%d" % (self.cur_page + 1, self.page_num))

    def CopyName(self, event):
        pyperclip.copy(event.GetEventObject().GetName())
        self.txtMsg.SetForegroundColour("SEA GREEN")
        self.txtMsg.SetLabel("已复制歌名")

    def CopyRecommond(self, event):
        pyperclip.copy(self.recommond)
        self.txtMsg.SetForegroundColour("SEA GREEN")
        self.txtMsg.SetLabel("已复制搜索建议")

    def OnKeyDown(self, event):
        keycode = event.GetRawKeyCode()
        if keycode == 27:
            self.Destroy()
        event.Skip()

    def OnMarkWY(self, event):
        song_id=event.GetEventObject().GetName()
        label = event.GetEventObject().GetLabel()
        tags=""
        if self.markSettingFrame:
            self.markSettingFrame.Destroy()
        if label=="☆":
            try:
                self.params_GetSongInfoWY["id"] = song_id
                self.params_GetSongInfoWY["ids"] = "[" + song_id + "]"
                res = requests.get(url=self.url_GetSongInfoWY, headers=self.headersWY, params=self.params_GetSongInfoWY,timeout=(5, 5))
                info = json.loads(res.text)
                if info["code"] == 200:
                    song=info["songs"][0]
                    tags+=song["name"]+"\n"
                    alias=";".join(song["alias"])
                    tags+=alias+"\n" if alias!="" else ""
                    artists=[artist["name"] for artist in song["artists"]]
                    tags += ";".join(artists)+"\n"
                    tags += song["album"]["name"]
                    self.markSettingFrame = MarkSettingFrame(self, "wy", song_id, tags, event.GetEventObject())
            except requests.exceptions.ConnectionError:
                dlg = wx.MessageDialog(None, "网络异常，请重试", "获取歌曲信息出错", wx.OK)
                dlg.ShowModal()
                dlg.Destroy()
            except requests.exceptions.ReadTimeout:
                dlg = wx.MessageDialog(None, "获取超时，请重试", "获取歌曲信息出错", wx.OK)
                dlg.ShowModal()
                dlg.Destroy()
        elif label=="★":
            tags=self.parent.wy_marks[song_id].replace(";","\n")
            self.markSettingFrame = MarkSettingFrame(self, "wy", song_id, tags, event.GetEventObject())

    def OnMarkQQ(self, event):
        song_id=event.GetEventObject().GetName().split(";")[0]
        label = event.GetEventObject().GetLabel()
        tags=""
        if self.markSettingFrame:
            self.markSettingFrame.Destroy()
        if label=="☆":
            try:
                self.params_GetSongInfoQQ["songid"] = song_id
                res = requests.get(url=self.url_GetSongInfoQQ, headers=self.headersQQ, params=self.params_GetSongInfoQQ, timeout=(5, 5))
                info = json.loads(res.text)
                if info["code"] == 0:
                    song=info["data"][0]
                    tags+=song["name"]+"\n"
                    alias = song["subtitle"]
                    tags += alias+"\n" if alias is not None and alias!="" else ""
                    artists=[singer["name"] for singer in song["singer"]]
                    tags += ";".join(artists)+"\n"
                    tags += song["album"]["name"]
                    self.markSettingFrame = MarkSettingFrame(self, "qq", song_id, tags, event.GetEventObject())
            except requests.exceptions.ConnectionError:
                dlg = wx.MessageDialog(None, "网络异常，请重试", "获取歌曲信息出错", wx.OK)
                dlg.ShowModal()
                dlg.Destroy()
            except requests.exceptions.ReadTimeout:
                dlg = wx.MessageDialog(None, "获取超时，请重试", "获取歌曲信息出错", wx.OK)
                dlg.ShowModal()
                dlg.Destroy()
        elif label=="★":
            tags=self.parent.qq_marks[song_id].replace(";","\n")
            self.markSettingFrame = MarkSettingFrame(self, "qq", song_id, tags, event.GetEventObject())

    def PreprocessCN(self,string):
        string=Converter('zh-hans').convert(string) #繁体转简体
        for k,v in preprocess_cn_rules.items(): #其他预处理
            string=re.sub(k,v,string)
        return string