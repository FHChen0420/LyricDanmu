# coding: utf-8
import wx
import requests
import time
import re
import os
import json
import pyperclip
from concurrent.futures import ThreadPoolExecutor,as_completed
import xml.dom.minidom

from SearchResult import SearchResult
from RoomSelectFrame import RoomSelectFrame
from ColorFrame import ColorFrame
from GeneralConfigFrame import GeneralConfigFrame
from RecordFrame import RecordFrame
from ShieldConfigFrame import ShieldConfigFrame
from CustomTextFrame import CustomTextFrame
from BiliLiveShieldWords import substitute,deal,generate_rule

from other_data import *
from util import *

session = requests.session()


# DONE

# TODO
# 1. custom_shield整合 

# THEN
# 1. 使用线程读取本地/收藏
# 7. 菜单栏
# 8. 网络情况检查
# 2. 同传弹幕捕获
# 1. 代理节点

# CANT
# 1. 听歌识曲

class LyricDanmu(wx.Frame):
    # -------------------------配置区开始--------------------------#

    title_version = "LyricDanmu v1.3.4"

    # 发送队列检测间隔（毫秒）
    fetch_interval = 30

    # 屏蔽词库更新间隔（秒）
    global_shield_update_interval_s = 3600

    # -------------------------配置区结束--------------------------#

    def __init__(self, parent):
        # 读取文件配置
        self.rooms={}
        self.wy_marks = {}
        self.qq_marks = {}
        self.locals = {}
        self.custom_shields = {}
        self.global_shields = {}
        self.custom_texts = []
        self.DefaultConfig()
        self.pool = ThreadPoolExecutor(max_workers=6)  # 线程池
        self.danmuQueue = []  # 弹幕发送队列
        self.CheckFile()
        if not self.ReadFile():
            return
        if self.no_proxy:
            os.environ["NO_PROXY"]="*"
        # 请求参数
        self.url_SendDanmu = "https://api.live.bilibili.com/msg/send"
        self.url_GetDanmuCfg = "https://api.live.bilibili.com/xlive/web-room/v1/dM/GetDMConfigByGroup"
        self.url_GetUserInfo = "https://api.live.bilibili.com/xlive/web-room/v1/index/getInfoByUser"
        self.url_SetDanmuCfg = "https://api.live.bilibili.com/xlive/web-room/v1/dM/AjaxSetConfig"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.221 Safari/537.36 SE 2.X MetaSr 1.0",
            "Origin": "https://live.bilibili.com",
            "Referer": "https://live.bilibili.com/",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,ja;q=0.7",
        }
        self.data_SendDanmu = {
            "color": 16777215,
            "fontsize": 25,
            # "mode":1,
            # "bubble":0,
            "msg": "",  # 弹幕内容
            "roomid": 0,  # 房间号
            "rnd": int(time.time()),
            "csrf_token": self.csrf,
            "csrf": self.csrf,
        }
        self.params_GetDanmuCfg = {
            "room_id": 0, # 房间号
        }
        self.params_GetUserInfo = {
            "room_id": 0, # 房间号
        }
        self.data_SetDanmuCfg = { #注：颜色和位置不能同时设置
            "room_id": 0, # 房间号
            #"color": "0xffffff", # 颜色
            #"mode": 1, # 位置
            "csrf": self.csrf,
            "csrf_token": self.csrf,
        }
        self.cookies = {
            "Cookie": self.cookie,
        }
        # Session
        requests.utils.add_dict_to_cookiejar(session.cookies,self.cookies)
        # 运行
        self.show_config = not self.init_show_lyric
        self.show_lyric = self.init_show_lyric
        self.show_import = False
        self.show_pin = True
        self.roomid = None
        self.roomName = None
        self.running = True
        self.init_lock = True
        self.auto_sending = False
        self.auto_pausing = False
        self.shield_changed = False
        self.colabor_mode = 0
        self.lyc_mod = 1
        self.pre_idx = 0
        self.recent_lyrics = [None,None]
        self.pool.submit(self.ThreadOfSend)
        self.ShowFrame(parent)

    def ShowFrame(self, parent):
        # 窗体
        wx.Frame.__init__(self, parent, title=self.title_version, style=wx.DEFAULT_FRAME_STYLE ^ (wx.RESIZE_BORDER | wx.MAXIMIZE_BOX) | wx.STAY_ON_TOP)
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(wx.EVT_MOVE, self.OnMove)
        self.Bind(wx.EVT_CHILD_FOCUS,self.OnFocus)
        self.searchFrame = None
        self.colorFrame = None
        self.generalConfigFrame = None
        self.customTextFrame = None
        self.shieldConfigFrame = ShieldConfigFrame(self)
        self.roomSelectFrame = RoomSelectFrame(self)
        self.recordFrame = RecordFrame(self)
        self.p0 = wx.Panel(self, -1, size=(450, 50), pos=(0, 0))
        self.p1 = wx.Panel(self, -1, size=(450, 360), pos=(0, 0))
        self.p2 = wx.Panel(self, -1, size=(450, 360), pos=(0, 0))
        self.p3 = wx.Panel(self, -1, size=(450, 85), pos=(0, 0))
        self.p4 = wx.Panel(self.p3, -1, size=(345,100), pos=(105,2))

        # P0 弹幕面板
        # 前缀选择
        self.cbbComPre = wx.ComboBox(self.p0, -1, pos=(15, 13), size=(60, -1), choices=["【", "", "", "", ""], style=wx.CB_DROPDOWN, value="")
        self.cbbComPre.Bind(wx.EVT_TEXT, self.CountText)
        self.cbbComPre.Bind(wx.EVT_COMBOBOX, self.CountText)
        # 弹幕输入框
        self.tcComment = wx.TextCtrl(self.p0, -1, "", pos=(82, 10), size=(255, 30), style=wx.TE_PROCESS_ENTER)
        self.tcComment.Bind(wx.EVT_TEXT_ENTER, self.SendComment)
        self.tcComment.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        self.tcComment.Bind(wx.EVT_TEXT, self.CountText)
        # 弹幕发送按钮
        self.btnComment = wx.Button(self.p0, -1, "00 ↩", pos=(345, 9), size=(47, 32))
        self.btnComment.Bind(wx.EVT_BUTTON, self.SendComment)
        # 同传配置拓展按钮
        self.btnExt = wx.Button(self.p0, -1, "▼", pos=(400, 9), size=(32, 32))
        self.btnExt.Bind(wx.EVT_BUTTON, self.ToggleConfigUI)

        # P3 配置主面板
        # 直播间选择
        self.btnRoom1 = wx.Button(self.p3, -1, "选择直播间", pos=(15, 3), size=(87, 32))
        self.btnRoom1.Bind(wx.EVT_BUTTON, self.ShowRoomSelectFrame)
        # 弹幕颜色/位置选择
        self.btnDmCfg1 = wx.Button(self.p3, -1, "██", pos=(15, 40), size=(43, 32))
        self.btnDmCfg1.SetBackgroundColour(wx.Colour(250,250,250))
        self.btnDmCfg2 = wx.Button(self.p3, -1, "⋘", pos=(59, 40), size=(43, 32))
        self.btnDmCfg2.SetFont(wx.Font(13, wx.DECORATIVE, wx.NORMAL, wx.NORMAL, faceName="微软雅黑"))
        self.btnDmCfg1.Disable()
        self.btnDmCfg2.Disable()
        self.btnDmCfg1.Bind(wx.EVT_BUTTON, self.ShowColorFrame)
        self.btnDmCfg2.Bind(wx.EVT_BUTTON, self.ChangeDanmuPosition)
        # 同传前缀与模式设置
        self.btnColaborCfg = wx.Button(self.p3, -1, "单人模式", pos=(125, 3), size=(87, 32))
        self.btnColaborCfg.Bind(wx.EVT_BUTTON,self.ShowColaborPart)
        # 常规设置按钮
        self.btnGeneralCfg = wx.Button(self.p3, -1, "应用设置", pos=(235, 3), size=(87, 32))
        self.btnGeneralCfg.Bind(wx.EVT_BUTTON,self.ShowGeneralConfigFrame)
        # 弹幕记录按钮
        self.btnShowRecord = wx.Button(self.p3, -1, "弹幕记录", pos=(125, 40), size=(87, 32))
        self.btnShowRecord.Bind(wx.EVT_BUTTON,self.ShowRecordFrame)
        # 屏蔽词管理按钮
        self.btnShieldCfg=wx.Button(self.p3,-1,"屏蔽词管理",pos=(235, 40), size=(87, 32))
        self.btnShieldCfg.Bind(wx.EVT_BUTTON,self.ShowShieldConfigFrame)

        # 多人联动设置
        wx.StaticText(self.p4, -1, "1", pos=(15, 10))
        wx.StaticText(self.p4, -1, "2", pos=(90, 10))
        wx.StaticText(self.p4, -1, "3", pos=(165, 10))
        wx.StaticText(self.p4, -1, "4", pos=(15, 42))
        wx.StaticText(self.p4, -1, "5", pos=(90, 42))
        self.tcPre1 = wx.TextCtrl(self.p4, -1, "【", pos=(25, 6), size=(55, 25), name="0")
        self.tcPre2 = wx.TextCtrl(self.p4, -1, "", pos=(100, 6), size=(55, 25), name="1")
        self.tcPre3 = wx.TextCtrl(self.p4, -1, "", pos=(175, 6), size=(55, 25), name="2")
        self.tcPre4 = wx.TextCtrl(self.p4, -1, "", pos=(25, 38), size=(55, 25), name="3")
        self.tcPre5 = wx.TextCtrl(self.p4, -1, "", pos=(100, 38), size=(55, 25), name="4")
        for x in (self.tcPre1, self.tcPre2, self.tcPre3, self.tcPre4, self.tcPre5):
            x.Bind(wx.EVT_TEXT,self.OnClbPreChange)
        self.ckbTabMod = wx.CheckBox(self.p4,-1,"Tab切换",pos=(162,43))
        self.ckbTabMod.SetForegroundColour("gray")
        self.ckbTabMod.SetValue(True)
        wx.StaticText(self.p4,-1,"❔",pos=(230,40)).SetToolTip(
            "联动模式下使用Tab键切换前缀，切换范围取决于联动人数\n" +
            "Shift+Tab键反向切换前缀，Alt+Tab键则会直接切换窗口\n" +
            "在任意模式下也可以直接使用Alt+数字键切换到指定的前缀\n")
        self.cbbClbMod = wx.ComboBox(self.p4, pos=(250, 6), size=(72, -1), choices=["单人模式", "双人联动", "三人联动", "四人联动", "五人联动"],style=wx.CB_READONLY)
        self.cbbClbMod.SetSelection(self.colabor_mode)
        self.cbbClbMod.Bind(wx.EVT_COMBOBOX, self.SetColaborMode)
        self.btnExitClbCfg = wx.Button(self.p4, -1, "◀  返  回  ", pos=(250, 37), size=(72, 27))
        self.btnExitClbCfg.Bind(wx.EVT_BUTTON, self.ExitColaborPart)

        # 歌词面板展开按钮
        self.btnExtLrc = wx.Button(self.p3, -1, "收起歌词", pos=(345, 3), size=(87, 32))
        self.btnExtLrc.Bind(wx.EVT_BUTTON, self.ToggleLyricUI)
        # 置顶按钮
        self.btnTop = wx.Button(self.p3, -1, "取消置顶", pos=(345, 40), size=(87, 32))
        self.btnTop.Bind(wx.EVT_BUTTON, self.TogglePinUI)

        # P1 歌词主面板
        # 直播间选择
        self.btnRoom2 = wx.Button(self.p1, -1, "选择直播间", pos=(15, 9), size=(87, 32))
        self.btnRoom2.Bind(wx.EVT_BUTTON,self.ShowRoomSelectFrame)
        # 歌词搜索
        if self.default_src=="wy":
            self.tcSearch = wx.TextCtrl(self.p1, -1, "", pos=(111, 10), size=(196, 30), style=wx.TE_PROCESS_ENTER, name="wy")
            self.btnSearch = wx.Button(self.p1, -1, "网易云 ↩", pos=(315, 9), size=(62, 32), name="wy")
            self.btnSearch2 = wx.Button(self.p1, -1, "QQ", pos=(382, 9), size=(49, 32), name="qq")
        else:
            self.tcSearch = wx.TextCtrl(self.p1, -1, "", pos=(111, 10), size=(196, 30), style=wx.TE_PROCESS_ENTER, name="qq")
            self.btnSearch = wx.Button(self.p1, -1, "QQ ↩", pos=(315, 9), size=(62, 32), name="qq")
            self.btnSearch2 = wx.Button(self.p1, -1, "网易云", pos=(382, 9), size=(49, 32), name="wy")
        self.tcSearch.Bind(wx.EVT_TEXT_ENTER, self.SearchLyric)
        self.btnSearch.Bind(wx.EVT_BUTTON, self.SearchLyric)
        self.btnSearch2.Bind(wx.EVT_BUTTON, self.SearchLyric)

        # 歌词静态文本
        self.lblLyrics = []
        self.lblTimelines = []
        for i in range(11):
            timeline_content=wx.StaticText(self.p1, -1, "", pos=(0, 140 + 20 * i), size=(35, 19), style=wx.ALIGN_CENTER | wx.ST_NO_AUTORESIZE)
            lyric_content = wx.StaticText(self.p1, -1, "", pos=(35, 140 + 20 * i), size=(375, 19), style=wx.ALIGN_CENTER | wx.ST_NO_AUTORESIZE)
            timeline_content.SetForegroundColour("gray")
            self.lblLyrics.append(lyric_content)
            self.lblTimelines.append(timeline_content)
        self.lblLyrics[4].SetForegroundColour("blue")
        self.lblTimelines[4].SetForegroundColour("blue")

        # 歌词弹幕配置
        txtLycMod = wx.StaticText(self.p1, -1, "模式", pos=(15, 54))
        txtLycPre = wx.StaticText(self.p1, -1, "前缀", pos=(15, 84))
        txtLycSuf = wx.StaticText(self.p1, -1, "后缀", pos=(15, 114))
        self.cbbLycMod = wx.ComboBox(self.p1, -1, pos=(45, 50), size=(57, -1), choices=["原版", "中文", "双语"], style=wx.CB_READONLY, value="中文")
        self.cbbLycPre = wx.ComboBox(self.p1, -1, pos=(45, 80), size=(57, -1), choices=self.prefixs, style=wx.CB_DROPDOWN, value=self.prefix)
        self.cbbLycSuf = wx.ComboBox(self.p1, -1, pos=(45, 110), size=(57, -1), choices=self.suffixs, style=wx.CB_DROPDOWN, value=self.suffix)
        self.cbbLycMod.Bind(wx.EVT_COMBOBOX, self.SetLycMod)

        # 歌词调整/发送按钮
        self.btnLycImpIn = wx.Button(self.p1, -1, "导入歌词", pos=(110, 49), size=(62, 42))
        self.btnCopyAll = wx.Button(self.p1, -1, "复制全文", pos=(110, 94), size=(62, 42))
        self.btnClearQueue = wx.Button(self.p1, -1, "清空队列", pos=(178, 49), size=(62, 42))
        self.btnCopyLine = wx.Button(self.p1, -1, "复制此句", pos=(178, 94), size=(62, 42))
        self.btnPrev = wx.Button(self.p1, -1, "▲", pos=(246, 49), size=(62, 42))
        self.btnNext = wx.Button(self.p1, -1, "▼", pos=(246, 94), size=(62, 42))
        self.btnSend = wx.Button(self.p1, -1, "手动发送", pos=(315, 49), size=(62, 42)) #116
        self.btnCustomText = wx.Button(self.p1, -1, "预设", pos=(382, 49), size=(49, 42))
        self.btnAutoSend = wx.Button(self.p1, -1, "自动 ▶", pos=(315, 94), size=(62, 42))
        self.btnStopAuto = wx.Button(self.p1, -1, "停止 □", pos=(382, 94), size=(49, 42))
        self.btnLycImpIn.Bind(wx.EVT_BUTTON, self.ToggleImportUI)
        self.btnClearQueue.Bind(wx.EVT_BUTTON, self.ClearQueue)
        self.btnCopyLine.Bind(wx.EVT_BUTTON, self.CopyLyricLine)
        self.btnCopyAll.Bind(wx.EVT_BUTTON, self.CopyLyricAll)
        self.btnPrev.Bind(wx.EVT_BUTTON, self.PrevLyric)
        self.btnNext.Bind(wx.EVT_BUTTON, self.NextLyric)
        self.btnSend.Bind(wx.EVT_BUTTON, self.OnSendLrcBtn)
        self.btnCustomText.Bind(wx.EVT_BUTTON, self.ShowCustomTextFrame)
        self.btnAutoSend.Bind(wx.EVT_BUTTON, self.OnAutoSendLrcBtn)
        self.btnStopAuto.Bind(wx.EVT_BUTTON, self.OnStopBtn)

        # 歌词进度滑块
        self.sldLrc = wx.Slider(self.p1, -1, 0, 0, 10, pos=(415, 155), size=(30, 195), style=wx.SL_VERTICAL)
        self.sldLrc.Bind(wx.EVT_SLIDER, self.OnLyricLineChange)
        self.lblCurLine = wx.StaticText(self.p1, -1, "", pos=(420, 137))
        self.lblMaxLine = wx.StaticText(self.p1, -1, "", pos=(420, 347))
        self.sldLrc.Show(False)

        # P2 歌词导入面板
        self.btnLycImpOut = wx.Button(self.p2, -1, "◀   返  回    ", pos=(15, 9), size=(96, 32))
        self.cbbImport = wx.ComboBox(self.p2, -1, pos=(271, 13), size=(60, -1), choices=["单语", "双语"], style=wx.CB_READONLY, value="单语")
        self.btnImport = wx.Button(self.p2, -1, "导入歌词", pos=(345, 9), size=(87, 32))
        self.btnLycImpOut.Bind(wx.EVT_BUTTON, self.ToggleImportUI)
        self.btnImport.Bind(wx.EVT_BUTTON, self.ImportLyric)
        self.cbbImport.Bind(wx.EVT_COMBOBOX, self.SynImpLycMod)
        # 歌词保存框
        self.tcImport = wx.TextCtrl(self.p2, -1, "", pos=(15, 49), size=(416, 180), style=wx.TE_MULTILINE)
        lblSongName = wx.StaticText(self.p2, -1, "歌名", pos=(15, 244))
        self.tcSongName = wx.TextCtrl(self.p2, -1, "", pos=(45, 240), size=(200, 27))
        lblArtists = wx.StaticText(self.p2, -1, "作者", pos=(263, 244))
        self.tcArtists = wx.TextCtrl(self.p2, -1, "", pos=(291, 240), size=(140, 27))
        lblTagDesc = wx.StaticText(self.p2, -1, "添加其他标签便于检索，使用分号或换行进行分割。", pos=(15, 272), size=(322,-1))
        self.tcTags = wx.TextCtrl(self.p2, -1, "", pos=(15, 292), size=(322, 65), style=wx.TE_MULTILINE)
        self.cbbImport2 = wx.ComboBox(self.p2, -1, pos=(346, 292), size=(85, -1), choices=["单语", "双语"], style=wx.CB_READONLY, value="单语")
        self.btnSaveToLocal = wx.Button(self.p2, -1, "保存至本地", pos=(345, 326), size=(87, 32))
        self.cbbImport2.Bind(wx.EVT_COMBOBOX, self.SynImpLycMod)
        self.btnSaveToLocal.Bind(wx.EVT_BUTTON,self.SaveToLocal)
        #
        self.tcSearch.SetFocus() if self.init_show_lyric else self.tcComment.SetFocus()
        self.p0.Show(True)
        self.p1.Show(True)
        self.p2.Show(False)
        self.p3.Show(True)
        self.p4.Show(False)
        self.ResizeUI()
        self.Show(True)

    def ShowCustomTextFrame(self,event):
        if self.customTextFrame:
            self.customTextFrame.Raise()
        else:
            self.customTextFrame=CustomTextFrame(self)

    def ShowRoomSelectFrame(self,event):
        if self.roomSelectFrame:
            self.roomSelectFrame.Raise()
        else:
            self.roomSelectFrame=RoomSelectFrame(self)

    def ShowShieldConfigFrame(self,event):
        self.shieldConfigFrame.Show(True)
        self.shieldConfigFrame.Raise()

    def ShowColaborPart(self,event):
        self.p4.Show(True)
        self.btnColaborCfg.Show(False)
        self.btnGeneralCfg.Show(False)
        self.btnShowRecord.Show(False)
        self.btnShieldCfg.Show(False)
        self.btnExtLrc.Show(False)
        self.btnTop.Show(False)
    
    def ExitColaborPart(self,event):
        self.btnColaborCfg.SetLabel(self.cbbClbMod.GetValue())
        self.p4.Show(False)
        self.btnColaborCfg.Show(True)
        self.btnGeneralCfg.Show(True)
        self.btnShowRecord.Show(True)
        self.btnShieldCfg.Show(True)
        self.btnExtLrc.Show(True)
        self.btnTop.Show(True)
    
    def OnClbPreChange(self,event):
        tcPre=event.GetEventObject()
        index=int(tcPre.GetName())
        pre1=tcPre.GetValue()
        pre2=pre1.lstrip()
        if pre1 != pre2:
            tcPre.SetValue(pre2)
            return
        pre2=re.sub(r"[ 　]{2,}$","　",pre2)
        if pre1 != pre2:
            tcPre.SetValue(pre2)
            tcPre.SetInsertionPointEnd()
            return
        self.cbbComPre.SetString(index, pre2)
        if index==self.pre_idx:
            self.cbbComPre.SetSelection(self.pre_idx)
        self.CountText(None)

    def ShowGeneralConfigFrame(self,event):
        if self.generalConfigFrame:
            self.generalConfigFrame.Raise()
        else:
            self.generalConfigFrame=GeneralConfigFrame(self)

    def GetCurrentDanmuConfig(self):
        self.params_GetUserInfo["room_id"]=self.roomid
        try:
            res=session.get(url=self.url_GetUserInfo,headers=self.headers,params=self.params_GetUserInfo,
                            timeout=(self.timeout_s,self.timeout_s))
        except requests.exceptions.ConnectionError:
            dlg = wx.MessageDialog(None, "网络异常，请重试", "获取弹幕配置出错", wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
            return False
        except requests.exceptions.ReadTimeout:
            dlg = wx.MessageDialog(None, "获取超时，请重试", "获取弹幕配置出错", wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
            return False
        try:
            data=json.loads(res.text)
            if not self.LoginCheck(data):    return
            if data["code"]==19002001 or data["message"]=="获取房间基础信息失败":
                dlg = wx.MessageDialog(None, "房间不存在", "获取弹幕配置出错", wx.OK)
                dlg.ShowModal()
                dlg.Destroy()
                return False
            config=data["data"]["property"]["danmu"]
            self.max_len=config["length"]
            self.cur_color=config["color"]
            self.cur_mode=config["mode"]
        except Exception as e:
            print(e)
            dlg = wx.MessageDialog(None, "解析错误，请重试", "获取弹幕配置出错", wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
            return False
        return True

    def GetUsableDanmuConfig(self):
        self.params_GetDanmuCfg["room_id"]=self.roomid
        try:
            res=session.get(url=self.url_GetDanmuCfg,headers=self.headers,params=self.params_GetDanmuCfg,
                            timeout=(self.timeout_s,self.timeout_s))
        except requests.exceptions.ConnectionError:
            dlg = wx.MessageDialog(None, "网络异常，请重试", "获取弹幕配置出错", wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
            return False
        except requests.exceptions.ReadTimeout:
            dlg = wx.MessageDialog(None, "获取超时，请重试", "获取弹幕配置出错", wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
            return False
        try:
            data=json.loads(res.text)
            if not self.LoginCheck(data):    return
            self.colors={}
            self.modes={}
            for group in data["data"]["group"]:
                for color in group["color"]:
                    if color["status"]==1:
                        self.colors[color["color"]]=color["name"]
            for mode in data["data"]["mode"]:
                if mode["status"]==1:
                    self.modes[mode["mode"]]=mode["name"]
            if len(self.modes)==1:
                self.btnDmCfg2.SetForegroundColour("gray")
            else:
                self.btnDmCfg2.SetForegroundColour("black")
        except Exception as e:
            print(e)
            dlg = wx.MessageDialog(None, "解析错误，请重试", "获取弹幕配置出错", wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
            return False
        return True

    def SetRoomid(self,roomid,name):
        if roomid==self.roomid and name==self.roomName:
            return
        if self.auto_sending:
            self.OnStopBtn(None)
        self.roomid=roomid
        self.roomName=name
        self.btnRoom1.SetLabel(name)
        self.btnRoom2.SetLabel(name)
        self.pool.submit(self.ThreadOfGetDanmuConfig)

    def ThreadOfGetDanmuConfig(self):
        self.btnRoom1.Disable()
        self.btnRoom2.Disable()
        self.btnDmCfg1.Disable()
        self.btnDmCfg2.Disable()
        if self.GetCurrentDanmuConfig():
            self.btnDmCfg1.SetForegroundColour(getRgbColor(self.cur_color))
            self.btnDmCfg2.SetLabel(bili_modes[str(self.cur_mode)])
            self.GetUsableDanmuConfig()
            self.btnDmCfg1.Enable()
            self.btnDmCfg2.Enable()
        else:
            self.roomid = None
            self.roomName = None
            self.btnRoom1.SetLabel("选择直播间")
            self.btnRoom2.SetLabel("选择直播间")
        self.btnRoom1.Enable()
        self.btnRoom2.Enable()
    
    def ThreadOfSetDanmuConfig(self,color,mode):
        self.data_SetDanmuCfg["room_id"]=self.roomid
        if color is not None:
            self.data_SetDanmuCfg["color"]=hex(int(color))
        else:
            self.data_SetDanmuCfg["mode"]=mode
        try:
            res=session.post(url=self.url_SetDanmuCfg,headers=self.headers,data=self.data_SetDanmuCfg,
                            timeout=(self.timeout_s,self.timeout_s))
        except requests.exceptions.ConnectionError:
            dlg = wx.MessageDialog(None, "网络异常，请重试", "保存弹幕配置出错", wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
            return
        except requests.exceptions.ReadTimeout:
            dlg = wx.MessageDialog(None, "获取超时，请重试", "保存弹幕配置出错", wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
            return
        data = json.loads(res.text)
        print(data)
        if data["code"]==0 and "data" in data.keys() and data["data"]["msg"]=="设置成功~":
            if color is not None:
                self.cur_color=color
                self.btnDmCfg1.SetForegroundColour(getRgbColor(color))
            else:
                self.cur_mode=mode
                self.btnDmCfg2.SetLabel(bili_modes[mode])
        else:
            self.Record("◆弹幕配置失败⋙ "+str(data))
            dlg = wx.MessageDialog(None, "设置失败，请重试", "保存弹幕配置出错", wx.OK)
            dlg.ShowModal()
            dlg.Destroy()

    def SendDanmu(self, roomid, msg, allowResend=True):
        if msg in self.recent_lyrics and len(msg) < self.max_len:
            msg+=("\u0592" if msg+"\u0594" in self.recent_lyrics else "\u0594")
        self.recent_lyrics.append(msg)
        self.recent_lyrics.pop(0)
        self.data_SendDanmu["msg"] = msg
        self.data_SendDanmu["roomid"] = roomid
        try:
            res = session.post(url=self.url_SendDanmu, headers=self.headers, data=self.data_SendDanmu,
                                timeout=(self.timeout_s,self.timeout_s))
            data=json.loads(res.text)
            errmsg=data["msg"]
            code=data["code"]
            if code!=0:
                if code==11000 and allowResend:
                    self.Record("⇩ [弹幕被吞,尝试重发]")
                    wx.MilliSleep(500)
                    return self.SendDanmu(roomid,msg,False)
                self.Record("▲发送失败⋙ "+msg)
                self.Record("(具体信息：[%d]%s)"%(code,data))
                return False
            if errmsg=="":
                self.Record(getTime()+"｜"+msg)
                return True
            elif errmsg=="msg in 1s":
                if allowResend:
                    self.Record("⇩ [间隔过短,尝试重发]")
                    wx.MilliSleep(500)
                    return self.SendDanmu(roomid,msg,False)
                else:
                    self.Record("▲间隔过短⋙ "+msg)
            elif errmsg=="msg repeat":
                self.Record("▲重复发送⋙ "+msg)
            elif errmsg in ["f","fire"]:
                self.Record("▲全局屏蔽⋙ "+msg)
                self.ShieldLog(msg)
            elif errmsg=="k":
                self.Record("▲房间屏蔽⋙ "+msg)
            else:
                self.Record("▲"+errmsg+"⋙ "+msg)
            return False
        except requests.exceptions.ConnectionError as e:
            if "Remote end closed connection without response" in str(e):
                if allowResend:
                    #self.Record("⇩ [远程连接异常关闭,尝试重发]")
                    wx.MilliSleep(200)
                    return self.SendDanmu(roomid,msg,False)
                else:
                    self.Record("▲远程连接异常关闭⋙ "+msg)
            self.Record("▲网络异常⋙ "+msg)
            dlg = wx.MessageDialog(None, "网络连接出错", "弹幕发送失败", wx.OK)
            print(e)
            dlg.ShowModal()
            dlg.Destroy()
            return False
        except requests.exceptions.ReadTimeout:
            self.Record("▲请求超时⋙ "+msg)
            print("[发送超时] %s"%msg)
            return False
        except Exception as e:
            self.Record("▲发送失败⋙ "+msg)
            self.Record("(具体信息：%s)"%str(e))
            print("[其它发送错误 %d] %s\n%s"%(json.loads(res.text)["code"],msg,e))
            return False

    def OnAutoSendLrcBtn(self,event):
        if self.init_lock or not self.has_timeline:
            return
        if self.auto_sending:
            if self.auto_pausing:
                resume_t=time.time()
                self.timeline_base+=resume_t-self.pause_t
                self.auto_pausing=False
                self.btnAutoSend.SetLabel("暂停 ⏸")
            else:
                self.pause_t=time.time()
                self.auto_pausing=True
                self.btnAutoSend.SetLabel("继续 ▶")
            return
        if self.roomid is None:
            dlg = wx.MessageDialog(None, "未指定直播间", "提示", wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
            return
        if not self.NextLyric(None):
            return
        if self.has_trans and self.lyc_mod == 2 and self.lblLyrics[3].GetLabel()!=self.lblLyrics[4].GetLabel():
            self.SendLyric(3)
        self.SendLyric(4)
        self.sldLrc.Disable()
        self.btnPrev.SetLabel("推迟半秒△")
        self.btnNext.SetLabel("提早半秒▽")
        self.btnStopAuto.SetLabel("停止 ■")
        self.btnAutoSend.SetLabel("暂停 ⏸")
        self.auto_sending=True
        self.auto_pausing=False
        self.pool.submit(self.ThreadOfAutoSend)

    def OnStopBtn(self,event):
        if self.init_lock:
            return
        self.auto_sending=False
        self.auto_pausing=False
        self.btnPrev.SetLabel("▲")
        self.btnNext.SetLabel("▼")
        self.btnStopAuto.SetLabel("停止 □")
        self.btnSend.SetLabel("手动发送")
        self.btnAutoSend.SetLabel("自动 ▶")
        self.sldLrc.Enable()

    def ThreadOfAutoSend(self):
        self.cur_t=self.timelines[self.oid]
        next_t=self.timelines[self.oid+1]
        self.timeline_base=time.time()-self.cur_t
        while self.auto_sending and next_t>=0:
            if self.auto_pausing:
                wx.MilliSleep(48)
                continue
            if self.cur_t>= next_t:
                self.NextLyric(None)
                if self.has_trans and self.lyc_mod == 2 and self.lblLyrics[3].GetLabel()!=self.lblLyrics[4].GetLabel():
                    self.SendLyric(3)
                self.SendLyric(4)
                next_t=self.timelines[self.oid+1]
            self.btnSend.SetLabel(getTimeLineStr(self.cur_t))
            self.cur_t = time.time()-self.timeline_base
            wx.MilliSleep(48)
        self.OnStopBtn(None)

    def DealLocalLyric(self,lrcO):
        res = []
        listO = lrcO.strip().split("\n")
        for o in listO:
            fs = self.SplitTnL(o)
            for f in fs:
                res.append(f)
        return sorted(res, key=lambda f:f[1])

    def DealSingleLyric(self, lrcO):
        res = {}
        listO = lrcO.strip().split("\n")
        for o in listO:
            fs = self.SplitTnL(o)
            for f in fs:
                res[f[3]]=f
        return sorted(res.values(), key=lambda f:f[1])

    def DealMixLyric(self, lrcO, lrcT):
        listO = lrcO.strip().split("\n")
        listT = lrcT.strip().split("\n")
        curTIdx = 0
        dictT = {}
        dictO = {}
        res = []
        for t in listT:
            fs = self.SplitTnL(t)
            for f in fs:
                if f[2] not in ["","//"]:
                    dictT[f[3]]=f
        dataT = sorted(dictT.values(), key=lambda f:f[1])
        maxTidx=len(dataT)
        for o in listO:
            fs = self.SplitTnL(o)
            for f in fs:
                dictO[f[3]]=f
        dataO = sorted(dictO.values(), key=lambda f:f[1])
        for f in dataO:
            res.append(f)
            for i in range(curTIdx,maxTidx):
                tf=dataT[i]
                if abs(tf[1]-f[1])<=0.07:  #对轴误差
                    if f[2] != "":
                        res.append([f[0],f[1],tf[2],f[3]]) #将轴对到与原版歌词一致
                        #res.append(tf) #直接使用翻译版歌词时轴
                        curTIdx+=1
                    else:
                        res.append(f)
                    break
            else:
                res.append(f)
        return res

    def SplitTnL(self,line):
        fs=[]
        parts=line.split("]")
        if len(parts)<=1:   return []
        content = parts[-1].strip()
        for tl in parts[0:-1]:
            mo=re.match(r"\[(\d+):(\d+)(\.\d*)?",tl)
            if mo is None:  continue
            t_min = int(mo.group(1))
            t_sec = int(mo.group(2))
            t_ms_str = ".00" if mo.group(3) is None else mo.group(3)
            t_ms=eval(t_ms_str)
            secnum = 60*t_min+t_sec+t_ms
            secfmt = "%2d:%02d"%(t_min,t_sec)
            secOrigin = "["+mo.group(1)+":"+mo.group(2)+t_ms_str+"]"
            fs.append([secfmt, secnum, content, secOrigin])
        return fs

    def RecvLyric(self,data):
        self.init_lock = False
        self.shield_changed = False
        self.OnStopBtn(None)
        self.sldLrc.Show(True)
        self.has_trans=data["has_trans"]
        self.has_timeline=True
        so=re.search(r"\[(\d+):(\d+)(\.\d*)?\]",data["lyric"])
        if so is None:
            tmpList=data["lyric"].strip().split("\n")
            tmpData=[["", 0, i.strip(), ""] for i in tmpList]
            self.has_timeline=False
        elif data["src"]=="local":
            tmpData=self.DealLocalLyric(data["lyric"])
        elif self.has_trans:
            tmpData=self.DealMixLyric(data["lyric"],data["tlyric"])
        else:
            tmpData=self.DealSingleLyric(data["lyric"])
        all_lyrics="\r\n".join([i[2] for i in tmpData])
        all_lyrics_tl="\r\n".join([i[3]+i[2] for i in tmpData])
        all_lyrics=re.sub(r" +"," ",all_lyrics)
        all_lyrics_tl=re.sub(r" +"," ",all_lyrics_tl)
        for k, v in html_transform_rules.items():
            all_lyrics = re.sub(k, v, all_lyrics)
            all_lyrics_tl = re.sub(k, v, all_lyrics_tl)
        self.lyric_raw=all_lyrics
        self.lyric_raw_tl=all_lyrics_tl
        all_lyrics=deal(all_lyrics,self.global_shields)
        all_lyrics = self.DealWithCustomShields(all_lyrics)
        all_lyric_list=all_lyrics.split("\r\n")
        for i in range(len(all_lyric_list)):
            tmpData[i][2]=all_lyric_list[i]
        tmpData.insert(0,["",-1,"<BEGIN>"])
        tmpData.append(["",-1,"<END>"])
        if self.has_trans:
            tmpData.insert(0,["",-1,"<BEGIN>"])
            tmpData.append(["",-1,"<END>"])
        self.llist=[]
        prev_empty = False
        for d in tmpData:  # 空行统一行数，单语一行，双语两行
            if d[2]!="<END>" and re.match(ignore_lyric_pattern,d[2].strip()):
                continue
            if d[2] != "":
                self.llist.append(d)
                prev_empty = False
            elif not prev_empty:
                self.llist.append(["",-2,""])
                if self.has_trans:
                    self.llist.append(["",-2,""])
                prev_empty = True
        self.lmax = len(self.llist)
        self.olist = []
        i = 0
        while i < self.lmax:
            if self.llist[i][2] != "":
                self.olist.append(i)
                i = i + 2 if self.has_trans else i + 1
            else:
                i += 1
        self.omax = len(self.olist)
        self.timelines=[]
        for i in self.olist:
            self.timelines.append(self.llist[i][1])
        self.oid = 0
        while self.oid + 2 < self.omax and re.search(r":|：|︰| - |翻唱", self.llist[self.olist[self.oid + 1]][2]):
            self.oid += 1
        self.lid = self.olist[self.oid]
        if self.has_trans and self.lyc_mod > 0:
            self.lid += 1
        self.sldLrc.SetRange(0, self.omax - 2)
        self.sldLrc.SetValue(self.oid)
        self.lblCurLine.SetLabel(str(self.oid))
        self.lblMaxLine.SetLabel(str(self.omax - 2))
        self.FlashLyric()
        self.show_lyric=True
        self.show_import=False
        self.ResizeUI()
        if self.has_timeline:
            self.btnAutoSend.SetLabel("自动 ▶")
            self.btnAutoSend.Enable()
            self.btnStopAuto.Enable()
        else:
            self.btnAutoSend.SetLabel("不支持\n自动播放")
            self.btnAutoSend.Disable()
            self.btnStopAuto.Disable()

    def SetLycMod(self, event):
        cur_lyc_mod = self.cbbLycMod.GetSelection()
        if not self.init_lock and self.has_trans and self.lyc_mod * cur_lyc_mod == 0 and self.lyc_mod + cur_lyc_mod > 0:
            self.lid = self.lid + (1 if cur_lyc_mod > 0 else -1)
            self.FlashLyric()
        self.lyc_mod = cur_lyc_mod

    def FlashLyric(self):
        for i in range(11):
            lid = self.lid + i - 4
            if lid >= 0 and lid < self.lmax:
                self.lblTimelines[i].SetLabel(self.llist[lid][0])
                self.lblLyrics[i].SetLabel(self.llist[lid][2])
            else:
                self.lblTimelines[i].SetLabel("")
                self.lblLyrics[i].SetLabel("")

    def CopyLyricLine(self, event):
        if self.init_lock:
            return
        pyperclip.copy(self.lblLyrics[4].GetLabel())

    def CopyLyricAll(self, event):
        if self.init_lock:
            return
        if self.has_timeline:
            dlg = wx.MessageDialog(None, "是否复制歌词时间轴？", "提示", wx.YES_NO|wx.NO_DEFAULT)
            pyperclip.copy(self.lyric_raw_tl if dlg.ShowModal()==wx.ID_YES else self.lyric_raw)
            dlg.Destroy()
        else:
            pyperclip.copy(self.lyric_raw)

    def ClearQueue(self,event):
        self.danmuQueue.clear()
        self.btnClearQueue.SetLabel("清空 [0]")

    def PrevLyric(self, event):
        if self.init_lock:
            return
        # 自动模式下，延缓进度
        if self.auto_sending and event is not None:
            self.timeline_base+=0.5
            self.cur_t-=0.5
            self.btnSend.SetLabel(getTimeLineStr(self.cur_t))
            return
        # 手动模式下，上一句
        if self.oid <= 0:
            return False
        self.sldLrc.SetValue(self.oid - 1)
        self.OnLyricLineChange(None)
        return True

    def NextLyric(self, event):
        if self.init_lock:
            return
        # 自动模式下，提早进度
        if self.auto_sending and event is not None:
            self.timeline_base-=0.5
            self.cur_t+=0.5
            self.btnSend.SetLabel(getTimeLineStr(self.cur_t))
            return
        # 手动模式下，下一句
        if self.oid + 2 >= self.omax:
            return False
        self.sldLrc.SetValue(self.oid + 1)
        self.OnLyricLineChange(None)
        return True

    def OnLyricLineChange(self, event):
        self.oid = self.sldLrc.GetValue()
        self.lblCurLine.SetLabel(str(self.oid))
        self.lid = self.olist[self.oid]
        if self.has_trans and self.lyc_mod > 0:
            self.lid += 1
        self.FlashLyric()

    def OnSendLrcBtn(self, event):
        if self.init_lock or self.auto_sending:
            return
        if self.roomid is None:
            dlg = wx.MessageDialog(None, "未指定直播间", "提示", wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
            return
        if not self.NextLyric(None):
            return
        if self.has_trans and self.lyc_mod == 2 and self.lblLyrics[3].GetLabel()!=self.lblLyrics[4].GetLabel():
            self.SendLyric(3)
        self.SendLyric(4)

    def SendLyric(self, line):
        pre = self.cbbLycPre.GetValue()
        suf = self.cbbLycSuf.GetValue()
        msg = pre + self.lblLyrics[line].GetLabel()
        if self.shield_changed:
            msg = self.DealWithCustomShields(msg)
        self.SendSplitDanmu(msg,pre,suf)

    def SendSplitDanmu(self, msg, pre, suf):
        if len(msg) > self.max_len:
            for k, v in compress_rules.items():
                msg = re.sub(k, v, msg)
        if len(msg) <= self.max_len:
            if len(msg+suf) <= self.max_len:
                self.danmuQueue.append([self.roomid,msg+suf])
            else:
                self.danmuQueue.append([self.roomid,msg])
            self.btnClearQueue.SetLabel("清空 [%d]" % len(self.danmuQueue))#
            return
        spaceIdx = []
        cutIdx = self.max_len
        for i in range(len(msg)):
            if msg[i] in " 　/":
                spaceIdx.append(i)
                spaceIdx.append(i + 1)
            elif msg[i] in "（“(「":
                spaceIdx.append(i)
            elif msg[i] in "，：！？）”…,:!?)」":
                spaceIdx.append(i + 1)
        if len(spaceIdx) > 0:
            for idx in spaceIdx:
                if idx <= self.max_len: cutIdx = idx
        if 1 + len(msg[cutIdx:]) + len(pre) > self.max_len:
            cutIdx = self.max_len
        self.danmuQueue.append([self.roomid,msg[:cutIdx]])
        self.btnClearQueue.SetLabel("清空 [%d]" % len(self.danmuQueue))#
        if msg[cutIdx:] in [")","）","」","】","\"","”"]:  return
        self.SendSplitDanmu(pre + "…" + msg[cutIdx:],pre,suf)

    def ImportLyric(self, event):
        lyric = self.tcImport.GetValue().strip()
        if lyric == "":
            dlg = wx.MessageDialog(None, "歌词不能为空", "歌词导入失败", wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
            return
        if lyric.count("\n") <= 4 or len(lyric) <= 50:
            dlg = wx.MessageDialog(None, "歌词内容过短", "歌词导入失败", wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
            return
        has_trans = self.cbbImport.GetSelection() == 1
        data={
            "src": "local",
            "has_trans": has_trans,
            "lyric": lyric,
        }
        self.RecvLyric(data)

    def SearchLyric(self, event):
        src=event.GetEventObject().GetName()
        words = self.tcSearch.GetValue().strip().replace("\\","")
        if words in ["","*"]:   return
        if self.searchFrame:
            self.searchFrame.Destroy()
        merge_mark_ids={}
        for k,v in self.wy_marks.items():
            merge_mark_ids["W"+k]=v
        for k,v in self.qq_marks.items():
            merge_mark_ids["Q"+k]=v
        if len(words)==1:
            mark_ids = self.SearchByOneCharTag(words, merge_mark_ids)
            local_names = self.SearchByOneCharTag(words, self.locals)
        else:
            mark_ids = self.SearchByTag(words, merge_mark_ids)
            local_names = self.SearchByTag(words, self.locals)
        self.searchFrame = SearchResult(self, src, words, mark_ids, local_names)

    def SendComment(self, event):
        pre = self.cbbComPre.GetValue()
        msg = self.tcComment.GetValue().strip()
        self.tcComment.SetFocus()
        if msg == "":
            return
        if self.roomid is None:
            dlg = wx.MessageDialog(None, "未指定直播间", "提示", wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
            return
        comment = pre + msg
        if len(comment) > 50:
            dlg = wx.MessageDialog(None, "弹幕内容过长", "弹幕发送失败", wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
            return
        comment = deal(comment,self.global_shields)
        comment = self.DealWithCustomShields(comment)
        suf = "】" if comment.count("【") > comment.count("】") else ""
        self.SendSplitDanmu(comment,pre,suf)
        self.tcComment.Clear()

    def SynImpLycMod(self,event):
        mode=event.GetEventObject().GetSelection()
        self.cbbImport.SetSelection(mode)
        self.cbbImport2.SetSelection(mode)

    def DefaultConfig(self):
        self.max_len = 20
        self.prefix = "【♪"
        self.suffix = "】"
        self.prefixs = ["【♪","【♬","【❀","【❄️","【★"]
        self.suffixs = ["","】"]
        self.enable_new_send_type=True
        self.send_interval = 750
        self.timeout_s = 5
        self.default_src = "wy"
        self.search_num = 18
        self.page_limit = 6
        self.init_show_lyric = True
        self.no_proxy = True
        self.cookie = ""
        self.csrf = ""

    def CheckFile(self):
        if not os.path.exists("config.txt"):
            self.SaveConfig()
        if not os.path.exists("rooms.txt"):
            with open("rooms.txt", "w", encoding="utf-8") as f:     f.write("")
        if not os.path.exists("marks_wy.txt"):
            with open("marks_wy.txt", "w", encoding="utf-8") as f:  f.write("")
        if not os.path.exists("marks_qq.txt"):
            with open("marks_qq.txt", "w", encoding="utf-8") as f:  f.write("")
        if not os.path.exists("shields.txt"):
            with open("shields.txt", "w", encoding="utf-8") as f:   f.write("")
        if not os.path.exists("shields_global.dat"):
            with open("shields_global.dat", "w", encoding="utf-8") as f:    f.write("")
        if not os.path.exists("custom_texts.txt"):
            with open("custom_texts.txt", "w", encoding="utf-8") as f:
                f.write(default_custom_text)
        if not os.path.exists("songs"):
            os.mkdir("songs")
        if not os.path.exists("logs"):
            os.mkdir("logs")

    def ReadFile(self):
        try:
            with open("config.txt", "r", encoding="utf-8") as f:
                for line in f:
                    if "=" not in line:     continue
                    sp = line.split("=", 1)
                    k,v=sp[0].strip(),sp[1].strip()
                    if k == "默认歌词前缀":
                        self.prefix = v
                    elif k == "默认歌词后缀":
                        self.suffix = v
                    elif k == "歌词前缀备选":
                        self.prefixs = v.split(",")
                    elif k == "歌词后缀备选":
                        self.suffixs = v.split(",")
                    elif k == "新版发送机制":
                        self.enable_new_send_type = True if v.lower()=="true" else False
                    elif k == "最低发送间隔":
                        interval = int(v)
                        if 500 <= interval <= 1500:
                            self.send_interval = interval
                            send_interval_check=True
                        else:
                            send_interval_check=False
                    elif k == "请求超时阈值":
                        tm_out = int(v)
                        if 2000 <= tm_out <= 10000:
                            self.timeout_s=tm_out/1000
                    elif k == "默认搜索来源":
                        self.default_src = "wy" if "qq" not in v.lower() else "qq"
                    elif k == "歌曲搜索条数":
                        search_num = int(v)
                        if 5 <= search_num <= 30:
                            self.search_num=search_num
                    elif k == "每页显示条数":
                        page_limit = int(v)
                        if 5 <= page_limit <= 8:
                            self.page_limit=page_limit
                    elif k == "默认展开歌词":
                        self.init_show_lyric = True if v.lower()=="true" else False
                    elif k == "忽略系统代理":
                        self.no_proxy = True if v.lower()=="true" else False
                    elif k == "cookie":
                        self.cookie = v
                if not send_interval_check:
                    self.send_interval = 750 if self.enable_new_send_type else 1050
                so = re.search(r"bili_jct=([0-9a-f]+);?", self.cookie)
                if so is not None:
                    self.csrf = so.group(1)
        except Exception as e:
            dlg = wx.MessageDialog(None, "读取config.txt失败", "启动出错", wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
            return False
        try:
            with open("rooms.txt", "r", encoding="utf-8") as f:
                for line in f:
                    mo=re.match(r"\s*(\d+)\s+(.+)",line)
                    if mo is not None:
                        self.rooms[mo.group(1)] = mo.group(2).rstrip()
        except Exception:
            dlg = wx.MessageDialog(None, "读取rooms.txt失败", "提示", wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
        try:
            with open("marks_wy.txt", "r", encoding="utf-8") as f:
                for line in f:
                    mo = re.match(r"\s*(\d+)\s+(.+)", line)
                    if mo is not None:
                        self.wy_marks[mo.group(1)] = mo.group(2).rstrip()
        except Exception:
            dlg = wx.MessageDialog(None, "读取marks_wy.txt失败", "提示", wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
        try:
            with open("marks_qq.txt", "r", encoding="utf-8") as f:
                for line in f:
                    mo = re.match(r"\s*(\d+)\s+(.+)", line)
                    if mo is not None:
                        self.qq_marks[mo.group(1)] = mo.group(2).rstrip()
        except Exception:
            dlg = wx.MessageDialog(None, "读取marks_qq.txt失败", "提示", wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
        try:
            with open("shields.txt", "r", encoding="utf-8") as f:
                for line in f:
                    mo = re.match(r"\s*(0|1)\s+(\S+)\s+(\S+)", line)
                    if mo is not None:
                        so=re.search(r"\\(?![1-9])|[\(\)\[\]\{\}\.\+\*\^\$\?\|]",mo.group(1))
                        if so is None:
                            self.custom_shields[mo.group(2)]=[int(mo.group(1)),mo.group(3)]
        except Exception:
            dlg = wx.MessageDialog(None, "读取shields.txt失败", "提示", wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
        try:
            scope = {"modified_time":0,"words":[],"rules":{}}
            with open("shields_global.dat","r",encoding="utf-8") as f:
                code="from BiliLiveShieldWords import get_len,measure,fill,r_pos\n"+f.read()
                exec(code,scope)
            for word in scope["words"]:
                generate_rule(word,scope["rules"])
            self.global_shields=scope["rules"]
            if time.time()-scope["modified_time"]>self.global_shield_update_interval_s:
                self.pool.submit(self.ThreadOfUpdateGlobalShields,2000)
            else:
                print("无需更新屏蔽词库")
        except Exception:
            dlg = wx.MessageDialog(None, "读取shields_global.dat失败", "提示", wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
        if not self.ReadCustomTexts():
            return False
        self.ReadLocalSongs()
        return True


    def ReadCustomTexts(self):
        default_data={
            "title":"(右键编辑)",
            "content":"",
        }
        try:
            DOMTree = xml.dom.minidom.parse("custom_texts.txt")
            collection = DOMTree.documentElement
            texts = collection.getElementsByTagName("text")
        except Exception:
            dlg = wx.MessageDialog(None, "读取custom_texts.txt失败", "提示", wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
            return False
        index=0
        for text in texts:
            data=default_data.copy()
            if text.hasAttribute("title") and text.getAttribute("title").strip()!="":
                data["title"]=text.getAttribute("title")
            data["content"]=text.childNodes[0].data
            self.custom_texts.append(data)
            index+=1
            if index>=4:
                break
        while index<4:
            self.custom_texts.append(default_data.copy())
            index+=1
        return True

    def ReadLocalSongs(self):
        fileList = os.listdir("songs")
        for file in fileList:
            filepath = "songs/" + file
            if not os.path.isfile(filepath):
                continue
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                    mo=re.search(r"<name>([\S\s]*?)</name>\s+?<artists>([\S\s]*?)</artists>\s+?<tags>([\S\s]*?)</tags>\s+?<type>([\S\s]*?)</type>\s+?<lyric>([\S\s]*?)</lyric>",content)
                    if mo is None:
                        continue
                    name =re.sub(r";|；","",mo.group(1))
                    artists=re.sub(r";|；","",mo.group(2))
                    lang = "双语" if mo.group(4).strip() == "双语" else "单语"
                    self.locals[file]=name+";"+artists+";"+lang+";"+mo.group(3)
            except Exception as e:
                print("ReadLocalSongs:")
                print(e)
                pass

    def TogglePinUI(self, event):
        self.show_pin = not self.show_pin
        self.ToggleWindowStyle(wx.STAY_ON_TOP)
        self.btnTop.SetLabel("取消置顶" if self.show_pin else "置顶窗口")

    def ToggleLyricUI(self, event):
        self.show_lyric = not self.show_lyric
        self.btnExtLrc.SetLabel("收起歌词" if self.show_lyric else "歌词面板")
        if self.show_lyric:
            self.btnExt.SetLabel("▼")
            self.tcSearch.SetFocus()
        else:
            self.tcComment.SetFocus()
        self.ResizeUI()

    def ToggleConfigUI(self, event):
        self.tcComment.SetFocus()
        self.show_config = not self.show_config
        self.btnExt.SetLabel("▲" if self.show_config else "▼")
        self.ResizeUI()

    def ToggleImportUI(self, event):
        self.show_import=not self.show_import
        self.ResizeUI()

    def ResizeUI(self):
        W,H=self.p0.GetSize()
        h1=self.p1.GetSize()[1]
        h3=self.p3.GetSize()[1]
        if self.show_lyric:
            H+=h1
            self.p0.SetPosition((0,h1))
            if self.show_import:
                self.p2.Show(True)
                self.p1.Show(False)
            else:
                self.p1.Show(True)
                self.p2.Show(False)
        else:
            self.p0.SetPosition((0, 0))
            self.p1.Show(False)
            self.p2.Show(False)
        if self.show_config:
            self.p3.SetPosition((0, H))
            self.p3.Show(True)
            H+=h3
        else:
            self.p3.Show(False)
        self.SetSize((W, H+25))# 考虑标题栏高度

    def OnKeyDown(self, event):
        keycode = event.GetKeyCode()
        if keycode == 9:  # Tab键
            if self.colabor_mode == 0 or not self.ckbTabMod.GetValue():
                return
            if event.GetModifiers()==wx.MOD_SHIFT:
                self.pre_idx = self.pre_idx - 1 if self.pre_idx > 0 else self.colabor_mode
            else:
                self.pre_idx = self.pre_idx + 1 if self.pre_idx < self.colabor_mode else 0
            self.cbbComPre.SetSelection(self.pre_idx)
            self.CountText(None)
            return
        if event.GetModifiers()==wx.MOD_ALT:
            if 49 <= keycode and keycode <= 53:  # 12345
                self.pre_idx = keycode - 49
                self.cbbComPre.SetSelection(self.pre_idx)
            return
        event.Skip()

    def CountText(self, event):
        comment = self.cbbComPre.GetValue() + self.tcComment.GetValue()
        label = "%02d" % len(comment) + (" ↩" if len(comment) <= 50 else " ×")
        self.btnComment.SetLabel(label)

    def ThreadOfSend(self):
        last_time = 0
        while self.running:
            try:
                wx.MilliSleep(self.fetch_interval)
                if len(self.danmuQueue) == 0:
                    continue
                danmu = self.danmuQueue.pop(0)
                interval_s = 0.001 * self.send_interval + last_time - time.time()
                if interval_s > 0:
                    wx.MilliSleep(int(1000 * interval_s))
                if self.enable_new_send_type: #新版机制
                    task = [self.pool.submit(self.SendDanmu, danmu[0], danmu[1])]
                    for i in as_completed(task):
                        pass
                else: #旧版机制
                    self.pool.submit(self.SendDanmu, danmu[0], danmu[1])
                last_time = time.time()
                self.btnClearQueue.SetLabel("清空 [%d]" % len(self.danmuQueue))  #
            except RuntimeError:
                pass
            except Exception as e:
                self.running = False
                dlg = wx.MessageDialog(None, "弹幕发送线程出错，请重启并将问题反馈给作者\n" + str(e), "发生错误", wx.OK)
                dlg.ShowModal()
                dlg.Destroy()
                break

    def Mark(self,src,song_id,tags):
        if src=="wy":
            self.wy_marks[song_id]=tags
        else:
            self.qq_marks[song_id]=tags

    def Unmark(self,src,song_id):
        if src=="wy":
            if song_id in self.wy_marks.keys():
                self.wy_marks.pop(song_id)
        else:
            if song_id in self.qq_marks.keys():
                self.qq_marks.pop(song_id)

    def SaveToLocal(self,event):
        lyric=self.tcImport.GetValue().strip()
        if lyric == "":
            dlg = wx.MessageDialog(None, "歌词不能为空", "歌词保存失败", wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
            return
        if lyric.count("\n") <= 4 or len(lyric) <= 50:
            dlg = wx.MessageDialog(None, "歌词内容过短", "歌词保存失败", wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
            return
        name=self.tcSongName.GetValue().strip()
        if name=="":
            dlg = wx.MessageDialog(None, "歌名不能为空", "歌词保存失败", wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
            return
        artists=self.tcArtists.GetValue().strip()
        tags=self.tcTags.GetValue().strip()
        has_trans=self.cbbImport2.GetSelection()==1
        self.CreateLyricFile(name,artists,tags,lyric,has_trans)

    def CreateLyricFile(self,name,artists,tags,lyric,has_trans):
        name=re.sub(r";|；","",name)
        filename=name
        lang="双语" if has_trans else "单语"
        for k,v in char_transform_rules.items():
            filename=filename.replace(k,v)
        tags = re.sub(r"\r?\n|；", ";", tags)
        tags = re.sub(r";+", ";", tags)
        if os.path.exists("songs/%s.txt"%filename):
            dlg = wx.MessageDialog(None, "歌词文件已存在，是否覆盖已有文件?", "提示", wx.YES_NO)
            if dlg.ShowModal()!=wx.ID_YES:
                dlg.Destroy()
                return False
            dlg.Destroy()
        try:
            with open("songs/%s.txt"%filename,"w",encoding="utf-8") as f:
                f.write("<name>" + name + "</name>\n")
                f.write("<artists>" + artists + "</artists>\n")
                f.write("<tags>" + tags + "</tags>\n")
                f.write("<type>" + lang + "</type>\n")
                f.write("<lyric>\n" + lyric +"\n</lyric>")
            self.locals[filename+".txt"]=name+";"+artists+";"+lang+";"+tags
            dlg = wx.MessageDialog(None, "歌词保存成功", "提示", wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
            return True
        except:
            dlg = wx.MessageDialog(None, "文件写入失败", "歌词保存失败", wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
            return False

    def ShowLocalInfo(self,file):
        filepath = "songs/" + file
        if not os.path.isfile(filepath):
            return False
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                mo = re.search(r"<lyric>([\S\s]*?)</lyric>",f.read())
                lyric="" if mo is None else mo.group(1).strip()
            raw_info=self.locals[file]
            info=raw_info.split(";",3)
            trans_id = 1 if info[2] == "双语" else 0
            self.tcSongName.SetValue(info[0])
            self.tcArtists.SetValue(info[1])
            self.cbbImport.SetSelection(trans_id)
            self.cbbImport2.SetSelection(trans_id)
            self.tcTags.SetValue(info[3].replace(";","\n"))
            self.tcImport.SetValue(lyric)
            self.show_lyric=True
            self.show_import=True
            self.ResizeUI()
            return True
        except Exception as e:
            print("ShowLocalInfo:")
            print(e)
            return False

    def SearchByOneCharTag(self, char, collection):
        res = []
        for song_id in collection:
            tags = collection[song_id].split(";")
            for tag in tags:
                if tag.lower().strip()==char:
                    res.append(song_id)
                    break
        return res

    def SearchByTag(self, words, collection):
        suggestions = []
        pattern=self.WrapUpPattern(words)
        regex = re.compile(pattern)
        for song_id in collection:
            sug = []
            tags = collection[song_id].split(";")
            for tag in tags:
                match = regex.search(tag.lstrip())
                if match:
                    sug.append((len(match.group()), match.start()))
            if len(sug) > 0:
                sug = sorted(sug)
                suggestions.append((sug[0][0], sug[0][1], song_id))
        return [x for _, _, x in sorted(suggestions)]

    def SaveConfig(self):
        try:
            with open("config.txt", "w", encoding="utf-8") as f:
                f.write("----------\n#弹幕配置#\n----------\n")
                f.write("默认歌词前缀=%s\n" % self.prefix)
                f.write("默认歌词后缀=%s\n" % self.suffix)
                f.write("歌词前缀备选=%s\n" % ",".join(self.prefixs))
                f.write("歌词后缀备选=%s\n" % ",".join(self.suffixs))
                f.write("新版发送机制=%s\n" % self.enable_new_send_type)
                f.write("最低发送间隔=%d\n" % self.send_interval)
                f.write("请求超时阈值=%d\n" % int(1000*self.timeout_s))
                f.write("----------\n#搜索配置#\n----------\n")
                f.write("默认搜索来源=%s\n" % ("网易云音乐" if self.default_src=="wy" else "QQ音乐"))
                f.write("歌曲搜索条数=%d\n" % self.search_num)
                f.write("每页显示条数=%d\n" % self.page_limit)
                f.write("----------\n#其它配置#\n----------\n")
                f.write("默认展开歌词=%s\n" % self.init_show_lyric)
                f.write("忽略系统代理=%s\n" % self.no_proxy)
                f.write("----------\n#账号配置#\n----------\n")
                f.write("cookie=%s\n" % self.cookie)
        except Exception as e:
            print("SaveConfig:")
            print(e)
            pass

    def OnClose(self, event):
        self.running = False
        self.SaveConfig()
        try:
            with open("rooms.txt", "w", encoding="utf-8") as f:
                for roomid in self.rooms:
                    f.write("%-15s%s\n" % (roomid, self.rooms[roomid]))
                f.flush()
        except Exception as e:
            print(e)
            pass
        try:
            with open("marks_wy.txt", "w", encoding="utf-8") as f:
                for song_id in self.wy_marks:
                    f.write("%-15s%s\n" % (song_id, self.wy_marks[song_id]))
                f.flush()
        except Exception as e:
            print(e)
            pass
        try:
            with open("marks_qq.txt", "w", encoding="utf-8") as f:
                for song_id in self.qq_marks:
                    f.write("%-15s%s\n" % (song_id, self.qq_marks[song_id]))
                f.flush()
        except Exception as e:
            print(e)
            pass
        try:
            with open("shields.txt", "w", encoding="utf-8") as f:
                for k,v in self.custom_shields.items():
                    f.write("%d %s %s\n" % (v[0],k,v[1]))
                f.flush()
        except Exception as e:
            print(e)
            pass
        try:
            with open("custom_texts.txt", "w", encoding="utf-8") as f:
                f.write("<texts>\n")
                for text in self.custom_texts:
                    f.write("<text title=\"%s\">\n%s\n</text>\n"%(text["title"],text["content"].strip()))
                f.write("</texts>")
                f.flush()
        except Exception as e:
            print(e)
            pass
        if os.path.exists("tmp.tmp"):
            try:    os.remove("tmp.tmp")
            except: pass
        self.Destroy()

    def ShowRecordFrame(self,event):
        self.recordFrame.Show()
        self.recordFrame.Restore()
        self.recordFrame.Raise()

    def ShowColorFrame(self,event):
        if self.colorFrame is not None:
            self.colorFrame.Destroy()
        self.colorFrame=ColorFrame(self)

    def ChangeDanmuPosition(self,event):
        mode_num=len(self.modes)
        if mode_num==1: return
        trans_dict={'1':'4','4':'1'} if mode_num==2 else {'1':'4','4':'5','5':'1'}
        self.pool.submit(self.ThreadOfSetDanmuConfig,None,trans_dict[str(self.cur_mode)])

    def OnMove(self,event):
        if self.colorFrame is not None:
            self.colorFrame.Show(False)

    def OnFocus(self,event):
        panel=event.GetEventObject().GetParent()
        if self.colorFrame is not None and panel!=self.colorFrame.panel:
            self.colorFrame.Show(False)
    
    def SetColaborMode(self,event):
        self.colabor_mode=self.cbbClbMod.GetSelection()
    
    def DealWithCustomShields(self,msg):
        for k,v in self.custom_shields.items():
            if v[0]==0 and re.search(r"\\[1-9]",k) is not None:
                msg=self.MultiDotBlock(k,msg)
            else:
                try:
                    msg=re.sub("(?i)"+" ?".join(k),v[1],msg)
                except Exception as e:
                    print("[DealWithCustomShields Error]",k,e)
                    pass
        return msg

    def MultiDotBlock(self,pattern,msg): #TODO 这里有一定冗余/是否考虑统一分隔符？
        origin_msg=msg
        try:
            pattern=re.sub(r"\\(?![1-9])","",pattern)
            groups=re.split(r"\\[1-9]",pattern)
            fills=[int(i) for i in re.findall(r"\\([1-9])",pattern)]
            n=len(fills)
            pat="(?i)" + "".join(["("+groups[i]+".*?)" for i in range(n)]) + "(%s)"%groups[n]
            repl="lambda x: (" + "+".join(["fill(x.group(1),%d)"%(len(groups[0])+int(fills[0]))] +
                ["x.group(%d)"%(i+1) for i in range(1,n+1)]) + ") if " + \
                " and ".join(["measure(x.group(%d),%d)"%(i+1,len(groups[i])+int(fills[i])) for i in range(n)]) + \
                " else x.group()"
            return substitute(pat,eval(repl),msg)
        except Exception as e:
            print("[regex fail]",e)
            return origin_msg
    
    def WrapUpPattern(self,words):
        words = re.sub(r"\s+", "", words)
        pattern = "∷".join(words)
        for k,v in regex_transform_rules.items():
            pattern = pattern.replace(k, v)
        pattern = "(?i)" + pattern.replace("∷", ".*?")
        return pattern

    def Record(self,message):
        try:
            self.recordFrame.tcRecord.AppendText(message+"\n")
        except Exception as e:
            print("[RecordFrame: Append Error]",e)
    
    def ShieldLog(self,string):
        try:
            path="logs/SHIELDED_%s.log"%getTime(fmt="%y_%m")
            with open(path,"a",encoding="utf-8") as f:
                f.write("%s｜%s\n"%(getTime(fmt="%m-%d %H:%M"),string))
        except Exception as e:
            print("[Logger: Log Error]",e)
    
    def LoginCheck(self,res):
        if res["code"]==-101 or "登录" in res["message"]:
            dlg = wx.MessageDialog(None, "账号未登录，请检查cookie配置", "错误", wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
            return False
        return True
    
    def ThreadOfUpdateGlobalShields(self,delay=0):    # 弄这个tmp主要还是避免同时打开多个工具时可能出现的资源共用问题
        if os.path.exists("tmp.tmp"):   return
        with open("tmp.tmp","w") as f:  f.write("本文件可删除")
        print("准备更新屏蔽词库")
        wx.MilliSleep(delay)
        self.shieldConfigFrame.btnUpdate.SetLabel("获取更新中…")
        #url_purge="https://purge.jsdelivr.net/gh/FHChen0420/bili_live_shield_words@main/BiliLiveShieldWords.py"
        url_fetch="https://cdn.jsdelivr.net/gh/FHChen0420/bili_live_shield_words@main/BiliLiveShieldWords.py"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.221 Safari/537.36 SE 2.X MetaSr 1.0",
        }
        try:
            r=requests.get(url=url_fetch,headers=headers,timeout=(5,10))
            so=re.search(r"# <DATA BEGIN>([\s\S]*?)# <DATA END>",r.text)
            code=so.group(1).replace("and not measure(x.group(3),4)","") #简化某条特殊规则
            # 写入内存
            scope = {"words":[],"rules":{}}
            code1="from BiliLiveShieldWords import get_len,measure,fill,r_pos\n"+code
            exec(code1,scope)
            for word in scope["words"]:
                generate_rule(word,scope["rules"])
            self.global_shields=scope["rules"]
            # 写入文件
            with open("shields_global.dat", "wb") as f:
                f.write(bytes(code,encoding="utf-8"))
                f.write(bytes("modified_time=%d"%int(time.time()),encoding="utf-8"))
                f.write(bytes("  # 最近一次更新时间：%s"%getTime(fmt="%m-%d %H:%M"),encoding="utf-8"))
            print("更新屏蔽词库成功")
            self.shieldConfigFrame.btnUpdate.SetLabel("更新完毕")
        except Exception as e:
            print("更新屏蔽词库失败\n",str(e))
            self.shieldConfigFrame.btnUpdate.SetLabel("失败 请重试")
        finally:
            try:    os.remove("tmp.tmp")
            except: pass


if __name__ == '__main__':
    app = wx.App(False)
    frame = LyricDanmu(None)
    app.MainLoop()
