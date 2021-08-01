import wx
import re
import requests
import pyperclip
import xml.dom.minidom
from math import ceil
from langconv import Converter
from SongMarkFrame import SongMarkFrame
from util import UIChange,setFont,getNodeValue,isEmpty,showInfoDialog
from constant import CN_LYRIC_PREPROCESS_RULES,LYRIC_IGNORE_RULES

class SongSearchFrame(wx.Frame):
    def __init__(self, parent, src, words, mark_ids, local_names):
        self.parent = parent
        self.src=src
        self.show_pin=parent.show_pin
        self.search_num = parent.search_num
        self.page_limit = parent.page_limit
        self.all_songs = []
        self.wyApi=parent.wyApi
        self.qqApi=parent.qqApi
        self.GetLocalSongs(local_names)
        self.GetMarkSongs(mark_ids)
        if src=="wy":
            self.GetNetworkSongsWY(words, mark_ids)
        else:
            self.GetNetworkSongsQQ(words, mark_ids)

    def GetLocalSongs(self,local_names):
        if len(local_names) == 0: return
        for file in local_names:
            info_raw = self.parent.locals[file]
            info=info_raw.split(";",4)
            song = {
                "my_local": True,
                "id": file,
                "name": info[0],
                "artists": [{"name":info[1]}],
                "album": {"name":"本地歌词"},
                "type": info[2],
                "tags": info[3],
            }
            self.all_songs.append(song)

    def GetMarkSongs(self,mark_ids):
        if len(mark_ids) == 0: return
        for mark_id in mark_ids:
            src,song_id=mark_id[0],mark_id[1:]
            try:
                if src=="W":    
                    data=self.wyApi.get_song_info(song_id,changeIP=True)
                else:
                    song_mid=song_id.split(";")[0]
                    data=self.qqApi.get_song_info(song_mid,changeIP=True)
                if data["code"] != (200 if src=="W" else 0):
                    raise Exception("Code: "+str(data["code"]))
                if len(data["songs" if src=="W" else "data"])==0:
                    song={
                        "my_mark": True,
                        "id": song_id,
                        "name": "[歌曲已失效，请删除收藏] [id:%s]"%song_id,
                        "alias": [],
                        "artists": [{"name":"?"}],
                        "album": {"name":"?"},
                    }
                    self.all_songs.append(song)
                elif src=="W":
                    data["songs"][0]["my_mark"] = True
                    data["songs"][0]["id"]=str(data["songs"][0]["id"])
                    self.all_songs += data["songs"]
                elif src=="Q":
                    qq_song = data["data"][0]
                    song={
                        "my_mark": True,
                        "id": song_id+";"+qq_song["mid"],
                        "name": qq_song["name"],
                        "alias": [] if isEmpty(qq_song["subtitle"]) else [qq_song["subtitle"]],
                        "artists": qq_song["singer"],
                        "album": qq_song["album"],
                    }
                    self.all_songs.append(song)
            except Exception as e:
                print("GetMarkSongs:",type(e),e)
                song={
                    "my_mark": True,
                    "id": "" if src=="W" else ";",
                    "name": "[获取失败]",
                    "alias": [],
                    "artists": [{"name":"?"}],
                    "album": {"name":"?"},
                }
                self.all_songs.append(song)

    def GetNetworkSongsWY(self, words, mark_ids):
        try:
            data=self.wyApi.search_songs(words,limit=self.search_num,changeIP=True)
            if data["code"] != 200:
                return showInfoDialog("获取歌曲列表失败", "搜索出错")
            if "abroad" in data.keys():
                return showInfoDialog("轮换IP出错，请反馈给作者", "搜索出错")
            elif "songs" not in data["result"] and len(self.all_songs)==0:
                return showInfoDialog("找不到相关歌曲", "提示")
            self.recommond = data["result"]["queryCorrected"][0] if "queryCorrected" in data["result"].keys() else None
            songs=data["result"]["songs"]
            for song in songs:
                if "W"+str(song["id"]) in mark_ids: continue
                song["id"]=str(song["id"])
                self.all_songs.append(song)
            self.ShowFrame(self.parent)
        except requests.exceptions.ConnectionError:
            return showInfoDialog("网络异常，请重试", "搜索出错")
        except requests.exceptions.ReadTimeout:
            return showInfoDialog("获取超时，请重试", "搜索出错")
        except Exception as e:
            print("GetNetworkSongsWY:",type(e),e)
            return showInfoDialog("解析错误，请重试", "搜索出错")
        return True

    def GetNetworkSongsQQ(self, words, mark_ids):
        try:
            data=self.qqApi.search_songs(words,limit=self.search_num,changeIP=True)
            if data["code"] != 0:
                return showInfoDialog("获取歌曲列表失败", "搜索出错")
            if data["subcode"]!=0 and len(self.all_songs)==0:
                return showInfoDialog("找不到相关歌曲", "提示")
            self.recommond = None
            qq_songs=data["data"]["song"]["list"]
            for qq_song in qq_songs:
                if "Q%d"%qq_song["songid"] in mark_ids:  continue
                song={
                    "id": "%d;%s"%(qq_song["songid"],qq_song["songmid"]), #id;mid
                    "name": qq_song["songname"],
                    "artists": [{"name": x["name"]} for x in qq_song["singer"]],
                    "alias": [],
                    "album": {"name": qq_song["albumname"]},
                }
                self.all_songs.append(song)
            self.ShowFrame(self.parent)
        except requests.exceptions.ConnectionError:
            return showInfoDialog("网络异常，请重试", "搜索出错")
        except requests.exceptions.ReadTimeout:
            return showInfoDialog("获取超时，请重试", "搜索出错")
        except Exception as e:
            print("GetNetworkSongsQQ:",type(e),e)
            return showInfoDialog("解析错误，请重试", "搜索出错")
        return True

    def ShowFrame(self, parent):
        # 窗体
        title="搜索结果 - "+("网易云" if self.src=="wy" else "QQ音乐")
        wx.Frame.__init__(self, parent, title=title, size=(520, self.page_limit * 50 + 120),
                          style=wx.DEFAULT_FRAME_STYLE ^ (wx.RESIZE_BORDER | wx.MAXIMIZE_BOX))
        if self.show_pin:
            self.ToggleWindowStyle(wx.STAY_ON_TOP)
        self.songMarkFrame=None
        self.p0 = wx.Panel(self, -1, pos=(0, 0), size=(520, 80))
        wins=parent.platform=="win"
        # 内容
        if self.recommond:
            txtRecommond = wx.StaticText(self.p0, -1, "建议：" + self.recommond, pos=(15, 10))
            setFont(txtRecommond,11 if wins else 15,bold=True)
            btnCopyRecommond = wx.Button(self.p0, -1, "复制\n建议", pos=(330, 10), size=(40, 40))
            btnCopyRecommond.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)  #
            btnCopyRecommond.Bind(wx.EVT_BUTTON, self.CopyRecommond)
        self.txtMsg = wx.StaticText(self.p0, -1, "", pos=(50, 40), size=(280, -1), style=wx.ALIGN_CENTER)
        setFont(self.txtMsg,13 if wins else 17,bold=True,name="微软雅黑" if wins else None)
        txtGetLyric = wx.StaticText(self.p0, -1, "歌词", pos=(387, 60))
        txtCopyName = wx.StaticText(self.p0, -1, "歌名", pos=(426, 60))
        txtMark = wx.StaticText(self.p0, -1, "收藏", pos=(465, 60))
        self.btnPrevPage = wx.Button(self.p0, -1, "◁", pos=(380, 10), size=(40, 40))
        self.btnPageNum = wx.Button(self.p0, -1, "", pos=(419, 10), size=(40, 40))
        self.btnNextPage = wx.Button(self.p0, -1, "▷", pos=(458, 10), size=(40, 40))
        setFont(self.btnPrevPage,14)
        setFont(self.btnNextPage,14)
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
                setFont(txtName,12 if wins else 16,bold=True,name="微软雅黑" if wins else None)
                btn1 = wx.Button(p, -1, "▶", pos=(380, 50 * j), size=(40, 40), name=song_id+";"+short_name)
                btn2 = wx.Button(p, -1, "✎", pos=(419, 50 * j), size=(40, 40), name=song["name"])
                btn3 = wx.Button(p, -1, "☆", pos=(458, 50 * j), size=(40, 40), name=song_id)
                setFont(btn1,14)
                setFont(btn2,14)
                setFont(btn3,14)
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
                    self.GetLyricTypeQQ(song["id"].split(";")[1],txt)
                j+=1

    def GetLyricTypeWY(self, song_id, txt):
        try:
            data=self.wyApi.get_lyric(song_id,changeIP=True)
            if data["code"] != 200:
                return UIChange(obj=txt,color="gray",label="错误")
            if "lrc" not in data.keys():
                return UIChange(obj=txt,color="red",label="无词")
            lrcO = data["lrc"]["lyric"]
            if isEmpty(lrcO):
                return UIChange(obj=txt,color="red",label="无词")
            if re.search(r"\[\d+:\d+(\.\d*)?\]", lrcO) is None:
                return UIChange(obj=txt,color="SEA GREEN",label="无轴")
            listO,line_num = lrcO.strip().split("\n"),0
            for o in listO:
                parts=o.split("]")
                content=parts[-1].strip()
                if content not in ["","<END>"] and not re.match(LYRIC_IGNORE_RULES,content):
                    line_num += len(parts)-1
            if isEmpty(data["tlyric"]["lyric"]):
                return UIChange(obj=txt,color="purple",label="单%d"%line_num)
            UIChange(obj=txt,color="blue",label="双%d"%line_num)
        except RuntimeError: pass
        except:
            try: UIChange(obj=txt,color="gray",label="重试")
            except RuntimeError: pass

    def GetLyricTypeQQ(self, song_mid, txt):
        try:
            data=self.qqApi.get_lyric(song_mid,changeIP=True)
            if data["code"] == -1901:
                return UIChange(obj=txt,color="red",label="无词")
            if data["code"] != 0:
                return UIChange(obj=txt,color="gray",label="错误")
            lrcO = data["lyric"]
            if isEmpty(lrcO) or "没有填词的纯音乐" in lrcO:
                return UIChange(obj=txt,color="red",label="无词")
            if re.search(r"\[\d+:\d+(\.\d*)?\]", lrcO) is None:
                return UIChange(obj=txt,color="SEA GREEN",label="无轴")
            listO,line_num = lrcO.strip().split("\n"),0
            for o in listO:
                parts=o.split("]")
                content=parts[-1].strip()
                if content not in ["","<END>"] and not re.match(LYRIC_IGNORE_RULES,content):
                    line_num += len(parts)-1
            if isEmpty(data["trans"]):
                return UIChange(obj=txt,color="purple",label="单%d"%line_num)
            UIChange(obj=txt,color="blue",label="双%d"%line_num)
        except RuntimeError: pass
        except:
            try: UIChange(obj=txt,color="gray",label="重试")
            except RuntimeError: pass

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
            showInfoDialog("读取本地文件失败", "获取信息出错")

    def GetNetworkLyricWY(self, event):
        try:
            self.txtMsg.SetForegroundColour("gray")
            self.txtMsg.SetLabel("获取歌词中...")
            info=event.GetEventObject().GetName().split(";",1)
            song_id,name = info[0],info[1]
            data=self.wyApi.get_lyric(song_id,changeIP=True)
            if data["code"] != 200:
                self.txtMsg.SetForegroundColour("red")
                self.txtMsg.SetLabel("获取歌词失败")
                return
            if "lrc" not in data.keys():
                self.txtMsg.SetForegroundColour("red")
                self.txtMsg.SetLabel("目标歌曲无歌词")
                return
            lrcO = data["lrc"]["lyric"]
            if isEmpty(lrcO):
                self.txtMsg.SetForegroundColour("red")
                self.txtMsg.SetLabel("目标歌曲无歌词")
                return
            if re.search(r"\[\d+:\d+(\.\d*)?\]", lrcO) is None:
                dlg = wx.MessageDialog(None, "是否以双语形式获取歌词？", "提示", wx.YES_NO|wx.NO_DEFAULT)
                has_trans = dlg.ShowModal() == wx.ID_YES
                ldata={
                    "src": "wy",
                    "has_trans": has_trans,
                    "lyric": lrcO,
                    "name": name,
                }
                self.parent.RecvLyric(ldata)
                dlg.Destroy()
                if has_trans:
                    self.txtMsg.SetForegroundColour("blue")
                    self.txtMsg.SetLabel("已获取双语歌词")
                else:
                    self.txtMsg.SetForegroundColour("purple")
                    self.txtMsg.SetLabel("已获取单语歌词")
                return
            lrcT = data["tlyric"]["lyric"]
            if isEmpty(lrcT):
                ldata={
                    "src": "wy",
                    "has_trans": False,
                    "lyric": lrcO,
                    "name": name,
                }
                self.parent.RecvLyric(ldata)
                self.txtMsg.SetForegroundColour("purple")
                self.txtMsg.SetLabel("已获取单语歌词")
            else:
                ldata={
                    "src": "wy",
                    "has_trans": True,
                    "lyric": lrcO,
                    "tlyric": self.PreprocessCN(lrcT),
                    "name": name,
                }
                self.parent.RecvLyric(ldata)
                self.txtMsg.SetForegroundColour("blue")
                self.txtMsg.SetLabel("已获取双语歌词")
        except requests.exceptions.ConnectionError:
            self.txtMsg.SetLabel("网络异常，请重试")
            showInfoDialog("网络异常，请重试", "获取歌词出错")
        except requests.exceptions.ReadTimeout:
            self.txtMsg.SetLabel("获取超时，请重试")
            showInfoDialog("获取超时，请重试", "获取歌词出错")
        except Exception as e:
            print("GetNetworkLyricWY:",type(e),e)
            self.txtMsg.SetLabel("解析错误，请重试")
            return showInfoDialog("解析错误，请重试", "搜索出错")

    def GetNetworkLyricQQ(self, event):
        try:
            self.txtMsg.SetForegroundColour("gray")
            self.txtMsg.SetLabel("获取歌词中...")
            info=event.GetEventObject().GetName().split(";",2)
            song_mid,name = info[1],info[2]
            data=self.qqApi.get_lyric(song_mid,changeIP=True)
            if data["code"] == -1901:
                self.txtMsg.SetForegroundColour("red")
                self.txtMsg.SetLabel("目标歌曲无歌词")
                return
            if data["code"] != 0:
                self.txtMsg.SetForegroundColour("red")
                self.txtMsg.SetLabel("获取歌词失败")
                return
            lrcO = data["lyric"]
            if isEmpty(lrcO) or "没有填词的纯音乐" in lrcO:
                self.txtMsg.SetForegroundColour("red")
                self.txtMsg.SetLabel("目标歌曲无歌词")
                return
            if re.search(r"\[\d+:\d+(\.\d*)?\]", lrcO) is None:
                dlg = wx.MessageDialog(None, "是否以双语形式获取歌词？", "提示", wx.YES_NO|wx.NO_DEFAULT)
                has_trans = dlg.ShowModal() == wx.ID_YES
                ldata={
                    "src": "qq",
                    "has_trans": has_trans,
                    "lyric": lrcO,
                    "name": name,
                }
                self.parent.RecvLyric(ldata)
                dlg.Destroy()
                if has_trans:
                    self.txtMsg.SetForegroundColour("blue")
                    self.txtMsg.SetLabel("已获取双语歌词")
                else:
                    self.txtMsg.SetForegroundColour("purple")
                    self.txtMsg.SetLabel("已获取单语歌词")
                return
            lrcT = data["trans"]
            if isEmpty(lrcT):
                ldata={
                    "src": "qq",
                    "has_trans": False,
                    "lyric": lrcO,
                    "name": name,
                }
                self.parent.RecvLyric(ldata)
                self.txtMsg.SetForegroundColour("purple")
                self.txtMsg.SetLabel("已获取单语歌词")
            else:
                ldata={
                    "src": "qq",
                    "has_trans": True,
                    "lyric": lrcO,
                    "tlyric": self.PreprocessCN(lrcT),
                    "name": name,
                }
                self.parent.RecvLyric(ldata)
                self.txtMsg.SetForegroundColour("blue")
                self.txtMsg.SetLabel("已获取双语歌词")
        except requests.exceptions.ConnectionError:
            self.txtMsg.SetLabel("网络异常，请重试")
            showInfoDialog("网络异常，请重试", "获取歌词出错")
        except requests.exceptions.ReadTimeout:
            self.txtMsg.SetLabel("获取超时，请重试")
            showInfoDialog("获取超时，请重试", "获取歌词出错")
        except Exception as e:
            print("GetNetworkLyricQQ:",type(e),e)
            self.txtMsg.SetLabel("解析错误，请重试")
            return showInfoDialog("解析错误，请重试", "搜索出错")

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
        if self.songMarkFrame:
            self.songMarkFrame.Destroy()
        if label=="☆":
            try:
                data=self.wyApi.get_song_info(song_id,changeIP=True)
                if data["code"] != 200:
                    return showInfoDialog("无法获取歌曲信息，请重试", "获取歌曲信息出错")
                song=data["songs"][0]
                tags+=song["name"]+"\n"
                alias=";".join(song["alias"])
                tags+=alias+"\n" if alias!="" else ""
                artists=[artist["name"] for artist in song["artists"]]
                tags += ";".join(artists)+"\n"
                tags += song["album"]["name"]
                self.songMarkFrame = SongMarkFrame(self, "wy", song_id, tags, event.GetEventObject())
            except requests.exceptions.ConnectionError:
                return showInfoDialog("网络异常，请重试", "获取歌曲信息出错")
            except requests.exceptions.ReadTimeout:
                return showInfoDialog("获取超时，请重试", "获取歌曲信息出错")
            except Exception as e:
                print("OnMarkWY:",type(e),e)
                return showInfoDialog("解析错误，请重试", "获取歌曲信息出错")
        elif label=="★":
            tags=self.parent.wy_marks[song_id].replace(";","\n")
            self.songMarkFrame = SongMarkFrame(self, "wy", song_id, tags, event.GetEventObject())

    def OnMarkQQ(self, event):
        song_id=event.GetEventObject().GetName().split(";")[0]
        label = event.GetEventObject().GetLabel()
        tags=""
        if self.songMarkFrame:
            self.songMarkFrame.Destroy()
        if label=="☆":
            try:
                data=self.qqApi.get_song_info(song_id,changeIP=True)
                if data["code"] != 0:
                    return showInfoDialog("无法获取歌曲信息，请重试", "获取歌曲信息出错")
                song=data["data"][0]
                tags+=song["name"]+"\n"
                alias = song["subtitle"]
                tags += alias+"\n" if alias is not None and alias!="" else ""
                artists=[singer["name"] for singer in song["singer"]]
                tags += ";".join(artists)+"\n"
                tags += song["album"]["name"]
                self.songMarkFrame = SongMarkFrame(self, "qq", song_id, tags, event.GetEventObject())
            except requests.exceptions.ConnectionError:
                return showInfoDialog("网络异常，请重试", "获取歌曲信息出错")
            except requests.exceptions.ReadTimeout:
                return showInfoDialog("获取超时，请重试", "获取歌曲信息出错")
            except Exception as e:
                print("OnMarkQQ:",type(e),e)
                return showInfoDialog("解析错误，请重试", "获取歌曲信息出错")
        elif label=="★":
            tags=self.parent.qq_marks[song_id].replace(";","\n")
            self.songMarkFrame = SongMarkFrame(self, "qq", song_id, tags, event.GetEventObject())

    def PreprocessCN(self,string):
        string=Converter('zh-hans').convert(string) #繁体转简体
        for k,v in CN_LYRIC_PREPROCESS_RULES.items(): #其他预处理
            string=re.sub(k,v,string)
        return string