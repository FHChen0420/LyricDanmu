# coding: utf-8
import asyncio
import os
import re
import sys
import time
import webbrowser
import xml.dom.minidom
from concurrent.futures import as_completed, ThreadPoolExecutor

import requests
import wx
import wx.html2
from pubsub import pub

from const.constant import *
from frame.color_select import ColorSelectFrame
from frame.custom_text import CustomTextFrame
from frame.danmu_record import DanmuRecordFrame
from frame.danmu_spread import DanmuSpreadFrame
from frame.general_config import GeneralConfigFrame
from frame.live_player import LivePlayerFrame
from frame.room_select import RoomSelectFrame
from frame.shield_config import ShieldConfigFrame
from frame.song_search import SongSearchFrame
from utils.api import *
from utils.live_anti_shield import BiliLiveAntiShield
from utils.live_chaser import RoomPlayerChaser
from utils.util import *


class MainFrame(wx.Frame):

    LD_VERSION = "v1.5.2"

    def __init__(self, parent=None):
        """B站直播同传/歌词弹幕发送工具"""
        # 获取操作系统信息
        self.platform="win" if sys.platform=="win32" else "mac"
        # 读取文件配置
        self.DefaultConfig()
        self.CheckFile()
        if not self.ReadFile(): return
        if self.no_proxy: os.environ["NO_PROXY"]="*"
        # 子窗体
        self.songSearchFrame = None                                 # 歌词搜索结果界面
        self.colorSelectFrame = None                                # 弹幕颜色选择界面
        self.generalConfigFrame = None                              # 应用设置界面
        self.customTextFrame = None                                 # 预设文本界面
        self.livePlayerFrame = None                                 # 追帧窗口
        self.danmuSpreadFrame = None                                # 弹幕转发配置界面
        self.shieldConfigFrame = None                               # 自定义屏蔽词配置界面
        self.roomSelectFrame = None                                 # 房间选择界面
        self.danmuRecordFrame = None                                # 弹幕发送记录界面
        # 消息订阅
        pub.subscribe(self.SpreadDanmu,"ws_recv")                   # 消息：监听到同传弹幕
        pub.subscribe(self.StartListening,"ws_start")               # 消息：开始监听房间内的弹幕
        pub.subscribe(self.SetSpreadButtonState,"ws_error")         # 消息：监听过程中出现错误/恢复
        # API
        self.blApi = BiliLiveAPI(self.cookies,(self.timeout_s,5))   # B站账号与直播相关接口
        self.wyApi = NetEaseMusicAPI()                              # 网易云音乐接口
        self.qqApi = QQMusicAPI()                                   # QQ音乐接口
        self.jdApi = JsdelivrAPI()                                  # Jsdelivr CDN接口
        # 界面参数
        self.show_config = not self.init_show_lyric                 # 是否展开功能面板
        self.show_lyric = self.init_show_lyric                      # 是否展开歌词面板
        self.show_import = False                                    # 是否显示歌词导入面板
        self.show_pin = True                                        # 是否置顶窗口
        self.show_msg_dlg = False                                   # 是否有未关闭的“网络异常”消息弹窗
        self.show_simple = False                                    # 是否启用简版模式
        self.init_lock = True                                       # 是否锁定歌词面板部分按钮
        # B站配置参数
        self.cur_acc = 0                                            # 账号编号（0或1）
        self.roomid = None                                          # 直播间号
        self.room_name = None                                       # 直播间名称
        self.colors = {}                                            # 用户可用的弹幕颜色
        self.modes = {}                                             # 用户可用的弹幕位置
        self.cur_color = 0                                          # 用户正在使用的弹幕颜色编号
        self.cur_mode = 1                                           # 用户正在使用的弹幕位置编号
        # 歌词参数
        self.cur_song_name = ""                                     # 歌曲名称
        self.last_song_name = ""                                    # 上一次发送的歌曲名称
        self.has_trans = False                                      # 歌词是否有翻译
        self.has_timeline = False                                   # 歌词是否有时间轴
        self.auto_sending = False                                   # 是否处于歌词自动播放模式
        self.auto_pausing = False                                   # 是否处于歌词自动播放的暂停状态
        self.lyric_raw=""                                           # 歌词原文本（不含时间轴）
        self.lyric_raw_tl=""                                        # 歌词原文本（含时间轴）
        self.timelines=[]                                           # 歌词时间轴列表
        self.llist=[]                                               # 歌词数据列表
        self.olist=[]                                               # 歌词原文索引列表
        self.lyc_mod = 1                                            # 歌词发送模式（0=原文，1=中文，2=双语）
        self.lid=0                                                  # 当前歌词行对应的歌词数据索引
        self.oid=0                                                  # 当前歌词行对应的原文索引
        self.lmax=0                                                 # 歌词数据列表大小
        self.omax=0                                                 # 歌词原文索引列表大小
        self.cur_t=0                                                # 歌词自动播放的当前进度    
        self.pause_t=0                                              # 歌词自动播放过程中暂停时的进度
        self.timeline_base=0                                        # 歌词自动播放的起始进度
        # 其他参数
        self.tmp_clipboard=""                                       # 临时剪贴板内容
        self.recent_danmu = {"_%d_"%i:0 for i in range(5)}          # 近期发送的弹幕字典（{弹幕内容：内容重复次数}）
        self.danmu_queue = []                                       # 待发送弹幕队列
        self.recent_history = []                                    # 评论框历史记录列表
        self.tmp_history = []                                       # 评论框历史记录列表（临时）
        self.running = True                                         # 工具是否正在运行
        self.history_state = False                                  # 是否正在调用评论框历史记录
        self.history_idx = 0                                        # 当前所选的评论框历史记录对应的索引
        self.colabor_mode = int(self.init_two_prefix)               # Tab键能切换的前缀个数-1 （范围0~4）
        self.pre_idx = -1                                           # 当前评论框前缀的索引
        self.transparent = 255                                      # 主窗口透明度
        self.shield_debug_mode = False                              # 是否启用屏蔽词调试模式
        # 追帧服务
        self.live_chasing = False                                   # 追帧服务是否正在运行
        self.playerChaser = RoomPlayerChaser("1")                   # 追帧工具
        self.playerFrameUseable = self.platform!="win" \
            or wx.html2.WebView.IsBackendAvailable(wx.html2.WebViewBackendEdge) # 当前系统是否支持自带窗口显示网页内容
        # 弹幕监听与转发
        self.ws_dict={}                                             # websocket字典
        self.sp_configs=[[[None],False,[]] for _ in range(3)]       # 同传转发配置列表
        self.sp_max_len = None                                      # 同传转发时的弹幕长度限制
        self.sp_error_count = 0                                     # 当前未正常运行的websocket连接数
        # 线程池与事件循环
        self.pool = ThreadPoolExecutor(max_workers=8)               # 通用线程池
        self.pool_ws = ThreadPoolExecutor(max_workers=12,thread_name_prefix="DanmuSpreader") # 转发用线程池
        self.loop = asyncio.new_event_loop()                        # 追帧用事件循环
        # 显示界面与启动线程
        self.ShowFrame(parent)
        if self.need_update_global_shields:
            self.pool.submit(self.ThreadOfUpdateGlobalShields)
        self.pool.submit(self.ThreadOfSend)

    def DefaultConfig(self):
        """加载默认配置"""
        self.rooms={}                                               # 房间字典（进入房间）
        self.sp_rooms={}                                            # 房间字典（转发弹幕）
        self.wy_marks = {}                                          # 网易云歌词收藏字典
        self.qq_marks = {}                                          # QQ音乐歌词收藏字典
        self.locals = {}                                            # 本地歌词字典
        self.custom_shields = {}                                    # 自定义屏蔽词字典
        self.custom_texts = []                                      # 预设文本列表
        self.danmu_log_dir = {}                                     # 弹幕日志目录列表
        self.translate_records = {}                                 # 同传内容记录字典
        self.translate_stat = []                                    # 同传统计列表
        self.max_len = 30                                           # 用户的弹幕长度限制
        self.prefix = "【♪"                                         # 歌词前缀
        self.suffix = "】"                                          # 歌词后缀
        self.prefixs = ["【♪","【♬","【❀","【❄️"]                  # 歌词前缀备选
        self.suffixs = ["","】"]                                    # 歌词后缀备选
        self.send_interval_ms = 750                                 # 弹幕发送间隔（毫秒）
        self.timeout_s = 3.05                                       # 弹幕发送超时阈值（秒）
        self.default_src = "wy"                                     # 歌词搜索默认来源
        self.search_num = 18                                        # 歌词搜索总条数
        self.page_limit = 6                                         # 歌词搜索每页显示条数
        self.lyric_offset = 0                                       # 歌词高亮偏移（0=当前播放行，1=待发送歌词）
        self.enable_lyric_merge = True                              # 是否启用歌词合并
        self.lyric_merge_threshold_s = 5.0                          # 歌词合并阈值
        self.add_song_name = False                                  # 是否在曲末添加歌名
        self.init_show_lyric = True                                 # 是否在启动时展开歌词面板
        self.init_show_record = False                               # 是否在启动时打开弹幕记录窗口
        self.no_proxy = True                                        # 是否禁用系统代理
        self.account_names=["",""]                                  # B站账号标注名称列表
        self.cookies=["",""]                                        # B站账号Cookie列表
        self.need_update_global_shields = True                      # 是否需要更新屏蔽词库
        self.tl_stat_break_min=10                                   # 同传统计允许的最大中断时长（分钟）
        self.tl_stat_min_count=20                                   # 同传统计要求的最低同传弹幕条数
        self.tl_stat_min_word_num=200                               # 同传统计要求的最低同传弹幕总字数
        self.show_stat_on_close=False                               # 是否在退出工具时显示同传统计
        self.anti_shield = BiliLiveAntiShield({},[])                # 全局屏蔽词处理工具
        self.anti_shield_ex = BiliLiveAntiShield({},[])             # 全局屏蔽词额外处理工具
        self.room_anti_shields = {}                                 # 房间屏蔽词处理工具字典
        self.init_two_prefix=False                                  # 是否将空前缀与【前缀作为默认的评论框前缀备选
        self.enable_rich_record=False                               # 是否启用富文本弹幕记录窗口
        self.record_fontsize=9 if self.platform=="win" else 13      # 弹幕记录窗口文字大小
        self.f_resend = True                                        # 弹幕触发全局屏蔽时是否自动重发
        self.f_resend_mark = True                                   # 弹幕重发时是否显示标识
        self.f_resend_deal = True                                   # 弹幕重发时是否对内容进行额外处理
        self.app_bottom_danmu = True                                # 是否将发出的弹幕在APP端置底
        self.cancel_danmu_after_failed = True                       # 长句前半段发送失败后是否取消后半段的发送

    def ShowFrame(self, parent):
        """布局并显示各类窗体控件"""
        # 窗体
        wx.Frame.__init__(self, parent, title="LyricDanmu %s - %s"%(self.LD_VERSION,self.account_names[0]),
            style=wx.DEFAULT_FRAME_STYLE ^ (wx.RESIZE_BORDER | wx.MAXIMIZE_BOX) | wx.STAY_ON_TOP)
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(wx.EVT_MOVE, self.OnMove)
        self.Bind(wx.EVT_CHILD_FOCUS,self.OnFocus)
        self.p0 = wx.Panel(self, -1, size=(450, 50), pos=(0, 0))
        self.p1 = wx.Panel(self, -1, size=(450, 360), pos=(0, 0))
        self.p2 = wx.Panel(self, -1, size=(450, 360), pos=(0, 0))
        self.p3 = wx.Panel(self, -1, size=(450, 85), pos=(0, 0))
        self.p4 = wx.Panel(self.p3, -1, size=(345,100), pos=(105,2))
        """ P0 弹幕输入面板 """
        # 前缀选择
        self.cbbComPre = wx.ComboBox(self.p0, -1, pos=(15, 13), size=(60, -1), choices=["【", "", "", "", ""], style=wx.CB_DROPDOWN, value="")
        self.cbbComPre.Bind(wx.EVT_TEXT, self.CountText)
        self.cbbComPre.Bind(wx.EVT_COMBOBOX, self.CountText)
        # 弹幕输入框
        self.tcComment = wx.TextCtrl(self.p0, -1, "", pos=(82, 10), size=(255, 30), style=wx.TE_PROCESS_ENTER|wx.TE_PROCESS_TAB)
        self.tcComment.Bind(wx.EVT_TEXT_ENTER, self.SendComment)
        self.tcComment.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        self.tcComment.Bind(wx.EVT_TEXT, self.CountText)
        self.tcComment.Bind(wx.EVT_TEXT, self.FetchFromTmpClipboard)
        self.tcComment.Bind(wx.EVT_TEXT_PASTE, self.OnPasteComment)
        # 弹幕发送按钮
        self.btnComment = wx.Button(self.p0, -1, "00 ↩", pos=(345, 9), size=(47, 32))
        self.btnComment.Bind(wx.EVT_BUTTON, self.SendComment)
        # 同传配置拓展按钮
        self.btnExt = wx.Button(self.p0, -1,  "▼" if self.init_show_lyric else "▲", pos=(400, 9), size=(32, 32))
        self.btnExt.Bind(wx.EVT_BUTTON, self.ToggleConfigUI)
        """ P1 歌词主面板 """
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
        self.tcSearch.Bind(wx.EVT_TEXT, self.FetchFromTmpClipboard)
        self.tcSearch.Bind(wx.EVT_TEXT_PASTE, self.OnPasteSearch)
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
        """ P2 歌词导入面板 """
        # 歌词导入部分
        self.btnLycImpOut = wx.Button(self.p2, -1, "◀   返  回    ", pos=(15, 9), size=(96, 32))
        self.cbbImport = wx.ComboBox(self.p2, -1, pos=(271, 13), size=(60, -1), choices=["单语", "双语"], style=wx.CB_READONLY, value="单语")
        self.btnImport = wx.Button(self.p2, -1, "导入歌词", pos=(345, 9), size=(87, 32))
        self.btnLycImpOut.Bind(wx.EVT_BUTTON, self.ToggleImportUI)
        self.btnImport.Bind(wx.EVT_BUTTON, self.ImportLyric)
        self.cbbImport.Bind(wx.EVT_COMBOBOX, self.SynImpLycMod)
        # 歌词保存部分
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
        """ P3 配置主面板 """
        # 直播间选择
        self.btnRoom1 = wx.Button(self.p3, -1, "选择直播间", pos=(15, 3), size=(87, 32))
        self.btnRoom1.Bind(wx.EVT_BUTTON, self.ShowRoomSelectFrame)
        # 弹幕颜色/位置选择
        self.btnDmCfg1 = wx.Button(self.p3, -1, "██", pos=(15, 40), size=(43, 32))
        self.btnDmCfg2 = wx.Button(self.p3, -1, "⋘", pos=(59, 40), size=(43, 32))
        if self.platform=="win":
            self.btnDmCfg1.SetBackgroundColour(wx.Colour(250,250,250))
            setFont(self.btnDmCfg2,13,name="微软雅黑")
        self.btnDmCfg1.Disable()
        self.btnDmCfg2.Disable()
        self.btnDmCfg1.Bind(wx.EVT_BUTTON, self.ShowColorSelectFrame)
        self.btnDmCfg2.Bind(wx.EVT_BUTTON, self.ChangeDanmuPosition)
        # 同传前缀与模式设置
        self.btnColaborCfg = wx.Button(self.p3, -1, "单人模式+" if self.init_two_prefix else "单人模式", pos=(115, 3), size=(87, 32))
        self.btnColaborCfg.Bind(wx.EVT_BUTTON,self.ShowColaborPart)
        # 常规设置按钮
        self.btnGeneralCfg = wx.Button(self.p3, -1, "应用设置", pos=(215, 3), size=(87, 32))
        self.btnGeneralCfg.Bind(wx.EVT_BUTTON,self.ShowGeneralConfigFrame)
        # 弹幕记录按钮
        self.btnShowRecord = wx.Button(self.p3, -1, "弹幕记录", pos=(115, 40), size=(87, 32))
        self.btnShowRecord.Bind(wx.EVT_BUTTON,self.ShowDanmuRecordFrame)
        # 屏蔽词管理按钮
        self.btnShieldCfg=wx.Button(self.p3,-1,"屏蔽词管理",pos=(215, 40), size=(87, 32))
        self.btnShieldCfg.Bind(wx.EVT_BUTTON,self.ShowShieldConfigFrame)
        # 同传弹幕转发配置按钮
        self.btnSpreadCfg = wx.Button(self.p3, -1, "转发", pos=(315, 3), size=(57,32))
        self.btnSpreadCfg.Bind(wx.EVT_BUTTON,self.ShowDanmuSpreadFrame)
        # 歌词面板展开按钮
        self.btnExtLrc = wx.Button(self.p3, -1, "歌词", pos=(375, 3), size=(57, 32))
        self.btnExtLrc.Bind(wx.EVT_BUTTON, self.ToggleLyricUI)
        self.btnExtLrc.SetForegroundColour("blue" if self.init_show_lyric else "black")
        # 追帧按钮
        self.btnChaser = wx.Button(self.p3, -1, "追帧", pos=(315,40), size=(57,32))
        self.btnChaser.Bind(wx.EVT_BUTTON, self.ShowPlayer)
        # 置顶按钮
        self.btnTop = wx.Button(self.p3, -1, "置顶", pos=(375, 40), size=(57, 32))
        self.btnTop.Bind(wx.EVT_BUTTON, self.TogglePinUI)
        """ P4 多人联动面板 """
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
        bindHint(wx.StaticText(self.p4,-1,"[?]",pos=(228,42)),
            "联动模式下使用Tab键切换前缀，切换范围取决于联动人数\n"
            "也可以直接使用Alt+数字键1~5来切换到指定的前缀"
        )
        self.cbbClbMod = wx.ComboBox(self.p4, pos=(250, 6), size=(72, -1), style=wx.CB_READONLY, choices=["不切换", "双前缀", "三前缀", "四前缀", "五前缀"])
        self.cbbClbMod.SetSelection(self.colabor_mode)
        self.cbbClbMod.Bind(wx.EVT_COMBOBOX, self.SetColaborMode)
        self.btnExitClbCfg = wx.Button(self.p4, -1, "◀  返  回  ", pos=(250, 37), size=(72, 27))
        self.btnExitClbCfg.Bind(wx.EVT_BUTTON, self.ExitColaborPart)
        # HotKey
        self.hkIncTp=wx.NewIdRef()
        self.hkDecTp=wx.NewIdRef()
        self.hkSimple=wx.NewIdRef()
        self.hkShield=wx.NewIdRef()
        self.hkCusText=wx.NewIdRef()
        self.RegisterHotKey(self.hkIncTp,wx.MOD_ALT,wx.WXK_UP)
        self.RegisterHotKey(self.hkDecTp,wx.MOD_ALT,wx.WXK_DOWN)
        self.RegisterHotKey(self.hkSimple,wx.MOD_ALT,wx.WXK_RIGHT)
        self.RegisterHotKey(self.hkShield,wx.MOD_ALT,ord("P"))
        self.RegisterHotKey(self.hkCusText,wx.MOD_ALT,ord("C"))
        self.Bind(wx.EVT_HOTKEY,self.IncreaseTransparent,self.hkIncTp)
        self.Bind(wx.EVT_HOTKEY,self.DecreaseTransparent,self.hkDecTp)
        self.Bind(wx.EVT_HOTKEY,self.ToggleSimpleMode,self.hkSimple)
        self.Bind(wx.EVT_HOTKEY,self.ToggleShieldDebugMode,self.hkShield)
        self.Bind(wx.EVT_HOTKEY,self.ShowCustomTextFrame,self.hkCusText)
        # MAC系统界面调整
        if self.platform=="mac":
            setFont(self,13)
            for obj in self.p1.Children:
                setFont(obj,10)
            for obj in [txtLycMod,txtLycPre,txtLycSuf,self.cbbLycMod,
                        self.cbbLycPre,self.cbbLycSuf,self.btnRoom2,self.tcSearch]:
                setFont(obj,13)
            for i in range(11):
                setFont(self.lblTimelines[i],12)
                setFont(self.lblLyrics[i],13)
        # 焦点与显示
        self.tcSearch.SetFocus() if self.init_show_lyric else self.tcComment.SetFocus()
        self.p0.Show(True)
        self.p1.Show(True)
        self.p2.Show(False)
        self.p3.Show(True)
        self.p4.Show(False)
        self.ResizeUI()
        self.Show(True)
        # 子窗体
        self.danmuSpreadFrame = DanmuSpreadFrame(self)
        self.shieldConfigFrame = ShieldConfigFrame(self)
        self.roomSelectFrame = RoomSelectFrame(self)
        self.danmuRecordFrame = DanmuRecordFrame(self)
        if self.platform=="mac":
            self.ShowRoomSelectFrame(None)

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

    def ShowGeneralConfigFrame(self,event):
        if self.generalConfigFrame:
            self.generalConfigFrame.Raise()
        else:
            self.generalConfigFrame=GeneralConfigFrame(self)

    def ShowDanmuSpreadFrame(self,event):
        self.danmuSpreadFrame.Show()
        self.danmuSpreadFrame.Restore()
        self.danmuSpreadFrame.Raise()

    def ShowDanmuRecordFrame(self,event):
        self.danmuRecordFrame.Show()
        self.danmuRecordFrame.Restore()
        self.danmuRecordFrame.Raise()

    def ShowColorSelectFrame(self,event):
        if self.colorSelectFrame is not None:
            self.colorSelectFrame.Destroy()
        self.colorSelectFrame=ColorSelectFrame(self)

    def ShowColaborPart(self,event):
        self.p4.Show(True)
        self.btnColaborCfg.Show(False)
        self.btnGeneralCfg.Show(False)
        self.btnShowRecord.Show(False)
        self.btnShieldCfg.Show(False)
        self.btnSpreadCfg.Show(False)
        self.btnChaser.Show(False)
        self.btnExtLrc.Show(False)
        self.btnTop.Show(False)
    
    def ShowPlayer(self,event):
        """显示追帧窗体"""
        if not self.live_chasing:
            if self.roomid is None:
                return showInfoDialog("未指定直播间", "提示")
            dlg = wx.MessageDialog(None, "是否启用直播流追帧服务？", "提示", wx.YES_NO|wx.NO_DEFAULT)
            if dlg.ShowModal()==wx.ID_YES:
                self.pool.submit(self.RunRoomPlayerChaser,self.roomid,self.loop)
                self.live_chasing=True
                self.btnChaser.SetForegroundColour("MEDIUM BLUE")
                dlg.Destroy()
            else:
                dlg.Destroy()
                return
        if not self.playerFrameUseable:
            webbrowser.open("http://127.0.0.1:8080/player.html")
            return
        dlg = wx.MessageDialog(None, "[是] 浏览器打开(推荐)　　　[否] 工具自带窗体打开", "选择追帧显示方式", wx.YES_NO|wx.YES_DEFAULT)
        res = dlg.ShowModal()
        if res==wx.ID_YES:
            webbrowser.open("http://127.0.0.1:8080/player.html")
        elif res==wx.ID_NO:
            if self.livePlayerFrame: self.livePlayerFrame.Raise()
            else:   self.livePlayerFrame=LivePlayerFrame(self)
        dlg.Destroy()
    
    def ExitColaborPart(self,event):
        mode_names=["单人模式","双人联动","三人联动","四人联动","五人联动"]
        sp_mode=self.colabor_mode==1 and (isEmpty(self.tcPre1.GetValue()) or isEmpty(self.tcPre2.GetValue()))
        label="单人模式+" if sp_mode else mode_names[self.cbbClbMod.GetSelection()]
        self.btnColaborCfg.SetLabel(label)
        self.p4.Show(False)
        self.btnColaborCfg.Show(True)
        self.btnGeneralCfg.Show(True)
        self.btnShowRecord.Show(True)
        self.btnShieldCfg.Show(True)
        self.btnSpreadCfg.Show(True)
        self.btnChaser.Show(True)
        self.btnExtLrc.Show(True)
        self.btnTop.Show(True)

    def IncreaseTransparent(self,event):
        self.transparent=min(255,self.transparent+15)
        self.SetTransparent(self.transparent)
    
    def DecreaseTransparent(self,event):
        self.transparent=max(30,self.transparent-15)
        self.SetTransparent(self.transparent)
    
    def ToggleSimpleMode(self,event):
        self.show_simple=not self.show_simple
        self.ToggleWindowStyle(wx.CAPTION)
        px,py=self.GetPosition()
        if self.show_simple:
            self.cbbComPre.SetPosition((0, 0))
            self.tcComment.SetPosition((60, 0))
            self.p0.SetPosition((0,0))
            self.p1.Show(False)
            self.p2.Show(False)
            self.SetPosition((px+25,py+35+int(self.show_lyric)*self.p1.GetSize()[1]))
            self.SetSize(315,30)
            self.p0.SetBackgroundColour("white")
        else:
            self.cbbComPre.SetPosition((15, 13))
            self.tcComment.SetPosition((82, 10))
            self.SetPosition((px-25,py-35-int(self.show_lyric)*self.p1.GetSize()[1]))
            self.p0.SetBackgroundColour(self.p1.GetBackgroundColour())
            self.ResizeUI()
            self.tcComment.SetFocus()
    
    def ToggleShieldDebugMode(self,event):
        self.shield_debug_mode=not self.shield_debug_mode
        if self.shield_debug_mode:
            showInfoDialog("屏蔽词调试模式已开启\n"
            "在该模式下，经弹幕输入框输入的内容或歌词内容\n"
            "不会进行全局屏蔽词处理，且禁用屏蔽词重发机制","调试提醒")
        else:
            showInfoDialog("屏蔽词调试模式已关闭","调试提醒")

    def TogglePinUI(self, event):
        self.show_pin = not self.show_pin
        self.ToggleWindowStyle(wx.STAY_ON_TOP)
        self.danmuSpreadFrame.ToggleWindowStyle(wx.STAY_ON_TOP)
        self.shieldConfigFrame.ToggleWindowStyle(wx.STAY_ON_TOP)
        self.btnTop.SetForegroundColour("black" if self.show_pin else "gray")

    def ToggleLyricUI(self, event):
        self.show_lyric = not self.show_lyric
        self.btnExtLrc.SetForegroundColour("medium blue" if self.show_lyric else "black")
        if self.show_lyric: self.tcSearch.SetFocus()
        else: self.tcComment.SetFocus()
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
        w,h=self.p0.GetSize()
        h1=self.p1.GetSize()[1]
        h3=self.p3.GetSize()[1]
        if self.show_lyric:
            h+=h1
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
            self.p3.SetPosition((0, h))
            self.p3.Show(True)
            h+=h3
        else:
            self.p3.Show(False)
        self.SetSize((w, h+25))# 考虑标题栏高度


    def ThreadOfGetDanmuConfig(self):
        """（子线程）获取弹幕配置"""
        UIChange(self.btnRoom1,enabled=False)
        UIChange(self.btnRoom2,enabled=False)
        UIChange(self.btnDmCfg1,enabled=False)
        UIChange(self.btnDmCfg2,enabled=False)
        if self.GetCurrentDanmuConfig():
            self.GetUsableDanmuConfig()
            UIChange(self.btnDmCfg1,color=getRgbColor(self.cur_color),enabled=True)
            UIChange(self.btnDmCfg2,label=BILI_MODES[str(self.cur_mode)],enabled=True)
        else:
            self.roomid = None
            self.room_name = None
            UIChange(self.btnRoom1,label="选择直播间")
            UIChange(self.btnRoom2,label="选择直播间")
        UIChange(self.btnRoom1,enabled=True)
        UIChange(self.btnRoom2,enabled=True)

    def ThreadOfSetDanmuConfig(self,color,mode):
        """（子线程）修改弹幕配置"""
        try:
            data=self.blApi.set_danmu_config(self.roomid,color,mode,self.cur_acc)
            if data["code"]!=0:
                return showInfoDialog("设置失败，请重试", "保存弹幕配置出错")
            if color is not None:
                self.cur_color=int(color,16)
                UIChange(self.btnDmCfg1,color=getRgbColor(self.cur_color))
            else:
                self.cur_mode=mode
                UIChange(self.btnDmCfg2,label=BILI_MODES[mode])
        except requests.exceptions.ConnectionError:
            return showInfoDialog("网络异常，请重试", "保存弹幕配置出错")
        except requests.exceptions.ReadTimeout:
            return showInfoDialog("获取超时，请重试", "保存弹幕配置出错")
        except Exception:
            return showInfoDialog("解析错误，请重试", "保存弹幕配置出错")
        return True

    def ThreadOfSend(self):
        """（子线程）发送弹幕"""
        last_time = 0
        while self.running:
            try:
                wx.MilliSleep(FETCH_INTERVAL_MS)
                if len(self.danmu_queue) == 0:
                    continue
                danmu = self.danmu_queue.pop(0)
                interval_s = 0.001 * self.send_interval_ms + last_time - time.time()
                if interval_s > 0:
                    wx.MilliSleep(int(1000 * interval_s))
                task = [self.pool.submit(self.SendDanmu, *danmu)]
                for _ in as_completed(task):    pass
                last_time = time.time()
                self.UpdateDanmuQueueLen()
            except RuntimeError:    pass
            except Exception as e:
                return showInfoDialog("弹幕发送线程出错，请重启并将问题反馈给作者\n" + str(e), "发生错误")

    def ThreadOfAutoSend(self):
        """（子线程）自动发送带时轴的歌词"""
        self.cur_t=self.timelines[self.oid]
        next_t=self.timelines[self.oid+1]
        self.timeline_base=time.time()-self.cur_t
        while self.auto_sending and next_t>=0:
            if self.auto_pausing:
                wx.MilliSleep(48)
                continue
            if self.cur_t>= next_t:
                self.NextLyric(None)
                if self.has_trans and self.lyc_mod == 2 and self.llist[self.lid-1][2]!=self.llist[self.lid][2]:
                    self.SendLyric(3)
                self.SendLyric(4)
                next_t=self.timelines[self.oid+1]
            UIChange(self.btnSend,label=getTimeLineStr(self.cur_t))
            self.cur_t = time.time()-self.timeline_base
            wx.MilliSleep(48)
        self.OnStopBtn(None)

    def ThreadOfUpdateGlobalShields(self):
        """（子线程）从云端更新B站直播间全局屏蔽词库"""
        if os.path.exists("tmp.tmp"):   return
        with open("tmp.tmp","w",encoding="utf-8") as f:  f.write("")
        UIChange(self.shieldConfigFrame.btnUpdateGlobal,label="获取更新中…")
        domains=("test1","testingcf","gcore","fastly","cdn") # 近期国内jsdelivr CDN域名遭污染，使用其子域名作为备用
        for domain in domains:
            try:
                code=""
                data=self.jdApi.get_latest_bili_live_shield_words(domain=domain)
                code=re.search(r"# <DATA BEGIN>([\s\S]*?)# <DATA END>",data).group(1)
                break
            except:
                pass
        else:
            UIChange(self.shieldConfigFrame.btnUpdateGlobal,label="无法获取更新")
        try:
            if code=="":    return
            # 写入内存
            scope = {"words":[],"rules":{},"ex_words":[],"ex_rules":{}}
            exec(code,scope)
            self.anti_shield=BiliLiveAntiShield(scope["rules"],scope["words"])
            self.anti_shield_ex=BiliLiveAntiShield(scope["ex_rules"],scope["ex_words"])
            # 写入文件
            with open("shields_global.dat", "wb") as f:
                f.write(bytes(code,encoding="utf-8"))
                f.write(bytes("modified_time=%d"%int(time.time()),encoding="utf-8"))
                f.write(bytes("  # 最近一次更新时间：%s"%getTime(fmt="%m-%d %H:%M"),encoding="utf-8"))
            UIChange(self.shieldConfigFrame.btnUpdateGlobal,label="词库更新完毕")
        except:
            UIChange(self.shieldConfigFrame.btnUpdateGlobal,label="云端数据有误")
        finally:
            if os.path.exists("tmp.tmp"):
                try: os.remove("tmp.tmp")
                except: pass

    def ThreadOfShowMsgDlg(self,content,title):
        """（子线程）显示消息弹窗"""
        if self.show_msg_dlg:   return
        self.show_msg_dlg=True
        showInfoDialog(content,title)
        wx.MilliSleep(3000)
        self.show_msg_dlg=False


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
            return showInfoDialog("未指定直播间", "提示")
        if not self.NextLyric(None):
            return
        if self.has_trans and self.lyc_mod == 2 and self.llist[self.lid-1][2]!=self.llist[self.lid][2]:
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
        if self.cur_song_name!=self.last_song_name:
            self.last_song_name=self.cur_song_name
            self.LogSongName("%8s\t%s"%(self.roomid,self.cur_song_name))

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

    def SynImpLycMod(self,event):
        mode=event.GetEventObject().GetSelection()
        self.cbbImport.SetSelection(mode)
        self.cbbImport2.SetSelection(mode)

    def OnLyricLineChange(self, event):
        self.oid = self.sldLrc.GetValue()
        self.lblCurLine.SetLabel(str(self.oid))
        self.lid = self.olist[self.oid]
        if self.has_trans and self.lyc_mod > 0:
            self.lid += 1
        wx.CallAfter(self.RefreshLyric)

    def ImportLyric(self, event):
        """导入本地歌词"""
        lyric = self.tcImport.GetValue().strip()
        if lyric == "":
            return showInfoDialog("歌词不能为空", "歌词导入失败")
        if lyric.count("\n") <= 4 or len(lyric) <= 50:
            return showInfoDialog("歌词内容过短", "歌词导入失败")
        has_trans = self.cbbImport.GetSelection() == 1
        ldata={
            "src": "local",
            "has_trans": has_trans,
            "lyric": lyric,
            "name": "",
        }
        self.RecvLyric(ldata)

    def OnKeyDown(self, event):
        keycode = event.GetKeyCode()
        if keycode == 315: # ↑键
            if len(self.recent_history)==0: return
            if self.history_state:
                if self.history_idx+1<len(self.tmp_history):
                    self.history_idx+=1
                self.tcComment.SetValue(self.tmp_history[self.history_idx])
                self.tcComment.SetInsertionPointEnd()
            else:
                self.tmp_history=self.recent_history[:]
                self.history_idx=0
                self.tcComment.SetValue(self.tmp_history[0])
                self.tcComment.SetInsertionPointEnd()
                self.history_state=True
            return
        if keycode == 317: # ↓键
            if not self.history_state:  return
            self.history_idx-=1
            if self.history_idx>=0:
                self.tcComment.SetValue(self.tmp_history[self.history_idx])
                self.tcComment.SetInsertionPointEnd()
            else:
                self.tcComment.Clear()
                self.history_state=False
            return
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
        """计算弹幕发送框的当前已输入内容的长度（含前缀长度）"""
        comment = self.cbbComPre.GetValue() + self.tcComment.GetValue()
        label = "%02d" % len(comment) + (" ↩" if len(comment) <= self.max_len*2.5 else " ×")
        self.btnComment.SetLabel(label)
        if event is not None:
            event.Skip()

    def SetLycMod(self, event):
        self.lyc_mod = self.cbbLycMod.GetSelection()
        if not self.init_lock:
            self.lid = self.olist[self.oid+self.lyric_offset]+int(self.has_trans and self.lyc_mod>0)
        self.RefreshLyric()

    def CopyLyricLine(self, event):
        """复制当前歌词全文"""
        if self.init_lock:  return
        wxCopy(self.lblLyrics[4].GetLabel())

    def CopyLyricAll(self, event):
        """复制歌词全文"""
        if self.init_lock:  return
        if self.has_timeline:
            dlg = wx.MessageDialog(None, "是否复制歌词时间轴？", "提示", wx.YES_NO|wx.NO_DEFAULT)
            wxCopy(self.lyric_raw_tl if dlg.ShowModal()==wx.ID_YES else self.lyric_raw)
            dlg.Destroy()
        else:
            wxCopy(self.lyric_raw)

    def ClearQueue(self,event):
        """清空待发送弹幕队列"""
        self.danmu_queue.clear()
        self.UpdateDanmuQueueLen(0)
    
    def UpdateDanmuQueueLen(self,n=None):
        """更新当前弹幕队列的长度显示"""
        n=len(self.danmu_queue) if n is None else n
        color="grey" if n<3 else "gold" if n<6 else "red"
        UIChange(self.btnClearQueue,label=f"清空 [{n}]")
        UIChange(self.danmuSpreadFrame.lblWait,label=f"待发:{n}",color=color)

    def PrevLyric(self, event):
        if self.init_lock:  return
        # 自动模式下，延缓进度
        if self.auto_sending and event is not None:
            self.timeline_base+=0.5
            self.cur_t-=0.5
            UIChange(self.btnSend,label=getTimeLineStr(self.cur_t))
            return
        # 手动模式下，上一句
        if self.oid <= 0:
            return False
        self.sldLrc.SetValue(self.oid - 1)
        self.OnLyricLineChange(None)
        return True

    def NextLyric(self, event):
        if self.init_lock:  return
        # 自动模式下，提早进度
        if self.auto_sending and event is not None:
            self.timeline_base-=0.5
            self.cur_t+=0.5
            UIChange(self.btnSend,label=getTimeLineStr(self.cur_t))
            return
        # 手动模式下，下一句
        if self.oid + 2 >= self.omax:
            return False
        self.sldLrc.SetValue(self.oid + 1)
        self.OnLyricLineChange(None)
        return True

    def OnSendLrcBtn(self, event):
        if self.init_lock or self.auto_sending: return
        if self.roomid is None:
            return showInfoDialog("未指定直播间", "提示")
        if not self.NextLyric(None):    return
        if self.has_trans and self.lyc_mod == 2 and self.llist[self.lid-1][2]!=self.llist[self.lid][2]:
            self.SendLyric(3)
        self.SendLyric(4)
        if self.cur_song_name!=self.last_song_name:
            self.last_song_name=self.cur_song_name
            self.LogSongName("%8s\t%s"%(self.roomid,self.cur_song_name))


    def OnClose(self, event):
        self.running = False
        self.OnStopBtn(None)
        self.Show(False)
        self.SaveConfig()
        self.SaveData()
        self.SaveTLRecords()
        self.ShowStatDialog()
        if os.path.exists("tmp.tmp"):
            try:    os.remove("tmp.tmp")
            except: pass
        for ws in self.ws_dict.values():
            ws.Stop()
        if not self.loop.is_closed():
            self.loop.call_soon_threadsafe(self.loop.stop)
        self.pool.shutdown()
        self.pool_ws.shutdown()
        self.Destroy()

    def ChangeDanmuPosition(self,event):
        mode_num=len(self.modes)
        if mode_num==1: return
        trans_dict={'1':'4','4':'1'} if mode_num==2 else {'1':'4','4':'5','5':'1'}
        self.pool.submit(self.ThreadOfSetDanmuConfig,None,trans_dict[str(self.cur_mode)])

    def OnMove(self,event):
        if self.colorSelectFrame is not None:
            self.colorSelectFrame.Show(False)

    def OnFocus(self,event):
        panel=event.GetEventObject().GetParent()
        if self.colorSelectFrame is not None and panel!=self.colorSelectFrame.panel:
            self.colorSelectFrame.Show(False)

    def OnPasteComment(self,event):
        """粘贴文本到弹幕发送框时触发。如果文本含有换行符，则进行相应处理"""
        text=wxPaste()
        if text is None:  return
        if "\n" in text or "\r" in text:
            wxCopy(re.sub("\s+"," ",text))
            self.tmp_clipboard=text
        else:
            self.tmp_clipboard=""
        event.Skip()
    
    def OnPasteSearch(self,event):
        """粘贴文本到歌词搜索框时触发。如果文本是QQ音乐听歌识曲字符串格式，则进行相应处理"""
        text=wxPaste()
        if text is None:  return
        mo=re.match("歌曲名：(.*?)，歌手名：",text)
        if mo is not None:
            wxCopy(re.sub(r"\(.*?\)|（.*?）","",mo.group(1)))
            self.tmp_clipboard=text
        else:
            self.tmp_clipboard=""
        event.Skip()
    
    def FetchFromTmpClipboard(self,event):
        """从剪贴板中获取临时的数据"""
        if self.tmp_clipboard!="":
            wxCopy(self.tmp_clipboard)
            self.tmp_clipboard=""
        event.Skip()
    
    def SetColaborMode(self,event):
        """设置在当前直播间中所使用的弹幕颜色"""
        self.colabor_mode=self.cbbClbMod.GetSelection()

    def SearchLyric(self, event):
        """搜索歌词（优先级：本地歌词>收藏歌词>非收藏歌词）"""
        src=event.GetEventObject().GetName()
        words = self.tcSearch.GetValue().strip().replace("\\","")
        if words in ["","*"]:   return
        if self.songSearchFrame:
            self.songSearchFrame.Destroy()
        merge_mark_ids={}
        for k,v in self.wy_marks.items():
            merge_mark_ids["W"+k]=v
        for k,v in self.qq_marks.items():
            merge_mark_ids["Q"+k]=v
        if len(words)==1:
            mark_ids = searchByOneCharTag(words, merge_mark_ids)
            local_names = searchByOneCharTag(words, self.locals)
        else:
            mark_ids = searchByTag(words, merge_mark_ids)
            local_names = searchByTag(words, self.locals)
        self.songSearchFrame = SongSearchFrame(self, src, words, mark_ids, local_names)

    def SendComment(self, event):
        """发送弹幕评论框中的内容"""
        pre = self.cbbComPre.GetValue()
        msg = self.tcComment.GetValue().strip()
        self.tcComment.SetFocus()
        if msg == "":
            return
        if self.roomid is None:
            return showInfoDialog("未指定直播间", "提示")
        comment = pre + msg
        if len(comment) > self.max_len*2.5:
            return showInfoDialog("弹幕内容过长", "弹幕发送失败")
        comment = self.AntiShield(comment)
        suf = "】" if comment.count("【") > comment.count("】") else ""
        self.AddDanmuToQueue(self.roomid,comment,DM_COMMENT,pre,suf)
        self.tcComment.Clear()
        self.tcComment.SetSelection(0,0)
        self.AddHistory(msg)
        self.history_state=False

    def SaveToLocal(self,event):
        """将自定义歌词保存到本地文件"""
        lyric=self.tcImport.GetValue().strip()
        lyric=lyric.replace("&","＆").replace("<","＜").replace(">","＞")
        if lyric == "":
            return showInfoDialog("歌词不能为空", "歌词保存失败")
        if lyric.count("\n") <= 4 or len(lyric) <= 50:
            return showInfoDialog("歌词内容过短", "歌词保存失败")
        name=self.tcSongName.GetValue().strip()
        if name=="":
            return showInfoDialog("歌名不能为空", "歌词保存失败")
        artists=self.tcArtists.GetValue().strip()
        tags=self.tcTags.GetValue().strip()
        has_trans=self.cbbImport2.GetSelection()==1
        self.CreateLyricFile(name,artists,tags,lyric,has_trans)


    def EnterRoom(self,roomid,rname):
        """设置当前直播间"""
        if not roomid:
            self.roomid,self.room_name=None,None
            self.btnRoom1.SetLabel("选择直播间")
            self.btnRoom2.SetLabel("选择直播间")
            self.btnDmCfg1.Disable()
            self.btnDmCfg2.Disable()
            if self.auto_sending: self.OnStopBtn(None)
            return
        self.room_name=rname
        self.btnRoom1.SetLabel(rname)
        self.btnRoom2.SetLabel(rname)
        if roomid==self.roomid: return
        if self.auto_sending: self.OnStopBtn(None)
        self.roomid=roomid
        self.playerChaser.roomId=roomid
        self.pool.submit(self.ThreadOfGetDanmuConfig)

    def GetLiveInfo(self,roomid):
        """根据房间号获取直播信息（主播名称、直播标题）"""
        try:
            data=self.blApi.get_room_info(roomid)
            live_title=data["data"]["room_info"]["title"].replace(",","，")
            liver_name=data["data"]["anchor_info"]["base_info"]["uname"].replace(",","，")
            liver_name=re.sub(r"(?i)[_\-]*(official|channel)","",liver_name)
            for k,v in FILENAME_TRANSFORM_RULES.items():
                liver_name=liver_name.replace(k,v)
            return liver_name,live_title
        except Exception as e:
            logDebug(f"[GetLiveInfo] {e}")
            return str(roomid),""

    def GetCurrentDanmuConfig(self,roomid=None):
        """获取用户在当前直播间内所使用的弹幕配置（颜色、位置、最大长度）"""
        try:
            roomid=self.roomid if roomid is None else roomid
            data=self.blApi.get_user_info(roomid,self.cur_acc)
            if not self.LoginCheck(data):    return False
            if data["code"]==19002001:
                return showInfoDialog("房间不存在", "获取弹幕配置出错")
            config=data["data"]["property"]["danmu"]
            self.max_len=config["length"]
            self.sp_max_len=min(30,self.max_len)
            self.cur_color=config["color"]
            self.cur_mode=config["mode"]
        except requests.exceptions.ConnectionError:
            return showInfoDialog("网络异常，请重试", "获取弹幕配置出错")
        except requests.exceptions.ReadTimeout:
            return showInfoDialog("获取超时，请重试", "获取弹幕配置出错")
        except Exception:
            return showInfoDialog("解析错误，请重试", "获取弹幕配置出错")
        return True

    def GetUsableDanmuConfig(self):
        """获取用户在当前直播间内的可用弹幕配置（颜色、位置）"""
        try:
            data=self.blApi.get_danmu_config(self.roomid,self.cur_acc)
            if not self.LoginCheck(data):    return False
            self.colors,self.modes={},{}
            for group in data["data"]["group"]:
                for color in group["color"]:
                    if color["status"]==1:
                        self.colors[color["color"]]=color["name"]
            for mode in data["data"]["mode"]:
                if mode["status"]==1:
                    self.modes[mode["mode"]]=mode["name"]
            UIChange(self.btnDmCfg2,color="gray" if len(self.modes)==1 else "black")
        except requests.exceptions.ConnectionError:
            return showInfoDialog("网络异常，请重试", "获取弹幕配置出错")
        except requests.exceptions.ReadTimeout:
            return showInfoDialog("获取超时，请重试", "获取弹幕配置出错")
        except Exception:
            return showInfoDialog("解析错误，请重试", "获取弹幕配置出错")
        return True

    def SendDanmu(self, roomid, msg, src, pre, max_len, try_times=2):
        """
        发送弹幕
        :param roomid: 直播间号
        :param msg: 弹幕内容（含前后缀）
        :param src: 弹幕来源(详见constant.py)
        :param msg: 弹幕前缀
        :param max_len: 弹幕长度限制
        :param try_times: 大于0表示弹幕发送失败后允许重发
        """
        if re.match("^…?[\s)）」』】’”\"\'\]][\s\U000E0020-\U000E0029】]*$",msg[len(pre):]):  return True
        origin_msg,remain_msg,succ_send=msg,"",False
        if len(origin_msg)>max_len:
            cut_idx=self.GetCutIndex(origin_msg,max_len,len(pre))
            msg=origin_msg[:cut_idx]
            remain_msg="…"+origin_msg[cut_idx:]
        if msg in self.recent_danmu.keys():
            num=self.recent_danmu[msg]
            self.recent_danmu[msg]=num+1
            mark=eval("'\\U000e002%d'"%(num%10))
            if len(msg) < max_len:
                msg = msg[:-1]+mark+"】" if msg[-1]=="】" else msg+mark
            else:
                msg = msg[:-1]+mark
        else:
            self.recent_danmu.pop(list(self.recent_danmu.keys())[0])
            self.recent_danmu[msg]=0
        try:
            mode = 4 if self.app_bottom_danmu else self.cur_mode # 测试功能：app端显示为底部弹幕
            data=self.blApi.send_danmu(roomid,msg,mode,number=self.cur_acc)
            if not self.LoginCheck(data): #用户未登入（cookies无效）
                self.UpdateRecord(msg,roomid,src,"7")
                return False
            errmsg,code=data["msg"],data["code"]
            if code==10030: #弹幕发送频率过高
                if try_times>0:
                    self.UpdateRecord("",roomid,src,"3+",False)
                    wx.MilliSleep(self.send_interval_ms)
                    succ_send=self.SendDanmu(roomid,msg,src,pre,max_len,try_times-2)
                else:
                    self.UpdateRecord(msg,roomid,src,"3")
            elif code==10031: #短期内发送了两条内容完全相同的弹幕
                self.UpdateRecord(msg,roomid,src,"4")
            elif code==11000: #弹幕被吞了（具体原因未知）
                if try_times>0:
                    self.UpdateRecord("",roomid,src,"5+",False)
                    wx.MilliSleep(self.send_interval_ms)
                    succ_send=self.SendDanmu(roomid,origin_msg,src,pre,max_len,try_times-2)
                else:
                    self.UpdateRecord(msg,roomid,src,"5")
            # elif code==-500: ... #弹幕长度超出限制
            # elif code==-102: ... #本次直播需要购票观看
            # elif code==-403: ... #当前直播间开启了全体禁言
            # elif code==1003: ... #在当前直播间被禁言
            elif code!=0: #其他发送失败情况
                logDebug(f"[SendDanmu] DATA={str(data)}")
                self.UpdateRecord(msg,roomid,src,"x")
                self.UpdateRecord("(%s)"%errmsg,roomid,src,"-",False)
            elif errmsg=="": #弹幕成功发送
                self.UpdateRecord(msg,roomid,src,"0")
                succ_send=True
            elif errmsg in ("f","fire"): #弹幕含有B站通用屏蔽词或特殊房间屏蔽词，或因B站偶尔抽风导致无法发送
                if self.f_resend and try_times>0 and not self.shield_debug_mode: # 注：屏蔽词调试模式下禁用屏蔽句重发
                    if self.f_resend_mark:
                        self.UpdateRecord("",roomid,src,"1+",False)
                    new_msg=self.anti_shield_ex.deal(origin_msg) if self.f_resend_deal else origin_msg
                    if new_msg!=origin_msg:
                        self.LogShielded(msg)
                    wx.MilliSleep(self.send_interval_ms+30)
                    succ_send=self.SendDanmu(roomid,new_msg,src,pre,max_len,try_times-2)
                else:
                    self.LogShielded(msg)
                    self.UpdateRecord(msg,roomid,src,"1")
            elif errmsg=="k": #弹幕含有当前直播间所设置的屏蔽词
                self.UpdateRecord(msg,roomid,src,"2")
            elif errmsg=="max limit exceeded": #当前房间弹幕流量过大，导致弹幕发送失败
                if try_times>0 or (src==DM_SPREAD and try_times==0):
                    self.UpdateRecord("",roomid,src,"6+",False)
                    wx.MilliSleep(self.send_interval_ms+200)
                    succ_send=self.SendDanmu(roomid,origin_msg,src,pre,max_len,try_times-1)
                else:
                    self.UpdateRecord(msg,roomid,src,"6")
            else:
                logDebug(f"[SendDanmu] ERRMSG={errmsg}")
                self.UpdateRecord(msg,roomid,src,"x")
                self.UpdateRecord("(具体信息：%s)"%errmsg,roomid,src,"-",False)
        except requests.exceptions.ConnectionError as e: #网络无连接/远程连接中断
            logDebug(f"[SendDanmu] TYPE={type(e)} DESC={e}")
            if "Connection aborted." in str(e):
                if try_times>0:
                    wx.MilliSleep(200)
                    succ_send=self.SendDanmu(roomid,origin_msg,src,pre,max_len,try_times-1)
                else:
                    self.UpdateRecord(msg,roomid,src,"C")
            else:
                self.pool.submit(self.ThreadOfShowMsgDlg,"网络连接出错","弹幕发送失败")
                self.UpdateRecord(msg,roomid,src,"A")
        except requests.exceptions.ReadTimeout: #API超时
            self.UpdateRecord(msg,roomid,src,"B")
        except BaseException as e: #其他异常
            logDebug(f"[SendDanmu] TYPE={type(e)} DESC={e}")
            self.UpdateRecord(msg,roomid,src,"X")
            self.UpdateRecord("(具体信息：%s)"%str(e),roomid,src,"-",False)
        finally:
            if remain_msg != "":
                if not succ_send and self.cancel_danmu_after_failed:
                    self.UpdateRecord(remain_msg,roomid,src,"Z")
                else:
                    wx.MilliSleep(self.send_interval_ms)
                    self.SendDanmu(roomid,remain_msg,src,pre,max_len)
            return succ_send

    def SpreadDanmu(self,roomid,speaker,content):
        """转发同传弹幕"""
        if self.sp_max_len is None:
            if not self.GetCurrentDanmuConfig(roomid):
                self.sp_max_len=20
        for cfg in self.sp_configs:
            to_room,from_rooms,spreading,speaker_filters=cfg[0][0],cfg[0][1:],cfg[1],cfg[2]
            if not spreading or to_room is None or roomid not in from_rooms: continue
            speaker=self.sp_rooms[roomid][1] if not speaker else speaker
            # 如果前缀过滤条件不为空，则只转发指定的前缀
            speaker_be_filtered=False
            for from_roomid,allowed_speakers in zip(from_rooms,speaker_filters):
                if roomid!=from_roomid or allowed_speakers=="": continue
                if speaker not in allowed_speakers.split(";"):
                    speaker_be_filtered=True
                    break
            if speaker_be_filtered: continue
            # 弹幕开头添加标识符U+0592避免循环转发（本工具不会转发以U+0592开头的同传弹幕）
            pre="\u0592"+speaker+"【"
            msg=self.AntiShield(pre+content,to_room)
            suf="】" if msg.count("【")>msg.count("】") else ""
            self.AddDanmuToQueue(to_room,msg,DM_SPREAD,pre,suf,self.sp_max_len)
    
    def StartListening(self,roomid):
        """建立与直播间之间的Websocket连接"""
        self.pool_ws.submit(self.ws_dict[roomid].Start)
    
    def SetSpreadButtonState(self,roomid=None,count=0,spreading=None):
        """检查Websocket运行情况，并更新主页面追帧按钮颜色进行提醒"""
        self.sp_error_count+=count
        spreading=self.danmuSpreadFrame.IsSpreading() if spreading is None else spreading
        if not spreading:
            self.btnSpreadCfg.SetLabel("转发")
            self.btnSpreadCfg.SetForegroundColour("black")
        elif self.sp_error_count>0:
            self.btnSpreadCfg.SetLabel(f"🌐×{self.sp_error_count}")
            self.btnSpreadCfg.SetForegroundColour("red")
        else:
            self.btnSpreadCfg.SetLabel("转发")
            self.btnSpreadCfg.SetForegroundColour("medium blue") 
        
    def RunRoomPlayerChaser(self,roomid,loop):
        """启用追帧服务"""
        asyncio.set_event_loop(loop)
        self.playerChaser.roomId=roomid
        if isPortUsed():
            showInfoDialog("8080端口已被占用,追帧服务启动失败","提示")
        else:
            self.playerChaser.serve(8080)
    
    def ShowStatDialog(self):
        """显示同传统计数据弹框"""
        stat_len=len(self.translate_stat)
        if not self.show_stat_on_close or stat_len==0:  return
        content="" if stat_len==1 else "本次同传共产生了%d条记录：\n"%stat_len
        for i in self.translate_stat[:3]:
            data=i.split(",")
            content+="主播：%s　　开始时间：%s　　持续时间：%s分钟\n弹幕数：%s　　总字数：%s　　平均速度：%s字/分钟\n\n"%\
                (data[2],data[0][5:-3],data[3],data[5],data[4],data[6])
        if stat_len>3:  content+="其余记录请在 logs/同传数据统计.csv 中进行查看"
        showInfoDialog(content,"同传统计数据")

    def SendLyric(self, line):
        """发送歌词弹幕"""
        pre = self.cbbLycPre.GetValue()
        suf = self.cbbLycSuf.GetValue()
        msg = self.llist[self.lid+line-4][2]
        message = self.AntiShield(pre+msg)
        self.AddDanmuToQueue(self.roomid,message,DM_LYRIC,pre,suf)
        self.AddHistory(msg)

    def AddDanmuToQueue(self, roomid, msg, src, pre="", suf="", max_len=None):
        """
        将弹幕添加到弹幕发送队列
        :param roomid: 直播间号
        :param msg: 弹幕内容(含前缀)
        :param src: 弹幕来源(详见constant.py)
        :param pre: 弹幕前缀
        :param suf: 弹幕后缀
        :param max_len: 弹幕长度限制(默认为当前账号在当前直播间的弹幕长度限制)
        """
        if max_len is None:
            max_len=self.max_len
        if len(msg) > max_len:
            for k, v in COMPRESS_RULES.items():
                msg = re.sub(k, v, msg)
        if not (len(msg)<=max_len and len(msg+suf)>max_len):
            msg+=suf
        self.danmu_queue.append([roomid,msg,src,pre,max_len])
        self.UpdateDanmuQueueLen()
        return
        
    def GetCutIndex(self,msg,max_len,pre_len=0):
        """获取合适的弹幕切割位置"""
        space_idx=[]
        cut_idx = max_len
        for i in range(max_len-1,pre_len,-1):
            if msg[i] in " 　/…": # 两侧均可切割
                space_idx.append(i+1)
                space_idx.append(i)
            elif msg[i] in "（“‘(「『": # 左侧可切割
                space_idx.append(i)
            elif msg[i] in "，。：！？）”’,:!?)」』~": # 右侧可切割
                space_idx.append(i+1)
            elif "O"!=charType(msg[i],True)!=charType(msg[i+1],True)!="O": # 汉字或假名 与 字母或数字 的边界可切割
                space_idx.append(i+1)
            else: continue
            if len(space_idx)>0 and space_idx[0]<max_len:
                cut_idx=space_idx[0]
                break
            if len(space_idx)>1:
                if space_idx[1]>=max_len-3: # 预留一些空间便于重发时添加字符
                    cut_idx=space_idx[1]
                break
        if cut_idx<=max_len*0.65 and 1+len(msg)-cut_idx+pre_len>max_len: # 如果切得太短，导致剩余部分太长，就多切一点
            cut_idx = max_len
        return cut_idx

    def GetRoomShields(self,roomid=None,update=False):
        """获取或更新指定房间的自定义屏蔽处理规则"""
        if roomid is None:
            return BiliLiveAntiShield({},[])
        if not update and roomid in self.room_anti_shields.keys():
            return self.room_anti_shields[roomid]
        rules,words={},[]
        for k,v in self.custom_shields.items():
            if v[2]!="" and roomid not in re.split("[,;，；]",v[2]): continue
            if v[0]==1:
                pat="(?i)"+transformToRegex(k," ?")
                rules[pat]=v[1].replace("`","\U000e0020")
            elif "#" in k:
                words.append(transformToRegex(k))
            else:
                pat="(?i)"+transformToRegex(k," ?")
                rules[pat]=lambda x:x.group()[0]+"\U000e0020"+x.group()[1:]
        shield = self.room_anti_shields[roomid] = BiliLiveAntiShield(rules,words)
        return shield

    def AntiShield(self,text,roomid=None):
        """对文本进行B站直播弹幕屏蔽词处理"""
        if not self.shield_debug_mode:
            if roomid is None:
                roomid=self.roomid
            text=self.GetRoomShields(roomid).deal(text)
            text=self.anti_shield.deal(text)
        return text

    def AddHistory(self,message):
        """将弹幕内容保存到近期弹幕历史记录中"""
        self.recent_history.insert(0,message)
        if len(self.recent_history)>10:
            self.recent_history.pop()

    @call_after
    def UpdateRecord(self,msg,roomid,src,res,log=True):
        """在弹幕发送记录界面以及转发界面更新记录，并输出到弹幕日志文件"""
        cur_time=int(time.time())
        if src==DM_SPREAD:
            if res=="0":
                label=f" {getTime(cur_time)}｜→{self.sp_rooms[roomid][0]}｜{msg[1:]}"
                self.danmuSpreadFrame.RecordSucc(label)
            elif log:
                self.danmuSpreadFrame.RecordFail()
        else:
            (pre,color)=(getTime(cur_time)+"｜","black") if res=="0" else ERR_INFO[res]
            self.danmuRecordFrame.AppendText("\n"+pre+msg,color)
        if log:
            self.LogDanmu(msg,roomid,src,res,cur_time)
    
    def SaveTLRecords(self):
        """记录近期同传数据至recent.dat文件，随后存储同传数据统计日志"""
        try:
            with open("logs/recent.dat","w",encoding="utf-8") as f:
                for k,v in self.translate_records.items():
                    if v[1] is None:   continue
                    f.write("%s,%d,%d,%s\n"%(k,v[0],v[1],v[2]))
        except Exception as e: logDebug(f"[SaveTLRecords] {e}")
        for k,v in self.translate_records.items():
            if v[1] is None:    continue
            stat_res=self.StatTLRecords(k,v[0],v[1],v[2])
            self.translate_stat+=list(stat_res.values())
    
    def StatTLRecords(self,roomid,start_time,end_time,live_title):
        """统计同传弹幕数据，并保存到本地csv文件"""
        dir_name=self.danmu_log_dir[roomid]
        liver_name=dir_name.split("_",1)[1]
        start_date_ts=strToTs(getTime(start_time,fmt="%y-%m-%d 00:00:00"))
        records,start_ts,last_ts,word_num,danmu_count={},start_time,start_time,0,0
        for ts in range(start_date_ts,end_time+1,86400):
            date=getTime(ts,fmt="%y-%m-%d")
            try:
                with open("logs/danmu/%s/%s.log"%(dir_name,date),"r",encoding="utf-8") as f:
                    for line in f:
                        mo=re.match(r"\[00\]\[(\d{2}:\d{2}:\d{2})\](.*?【.*)",line)
                        if not mo:  continue
                        ts=strToTs(getTime(start_time,fmt="%s %s"%(date,mo.group(1))))
                        if ts<start_time or ts>end_time:    continue
                        if ts>last_ts+self.tl_stat_break_min*60:
                            if word_num>=self.tl_stat_min_word_num and danmu_count>=self.tl_stat_min_count:
                                start_str=getTime(start_ts,fmt="%Y-%m-%d %H:%M:%S")
                                duration=(last_ts-start_ts)/60
                                records[start_str]="%s,%s,%s,%.1f,%d,%d,%.1f"%(start_str,live_title,liver_name,duration,word_num,danmu_count,word_num/duration)
                            start_ts,last_ts,word_num,danmu_count=ts,ts,0,0
                        else:
                            content=re.sub(r"^.*?【|[\[\]【】\u0592\u0594\U000e0020-\U000e0029]","",mo.group(2).strip())
                            word_num+=len(content)
                            danmu_count+=1
                            last_ts=ts
            except Exception as e:
                logDebug(f"[StatTLRecords] ReadError: DATE={date} {e}")
        if word_num>=self.tl_stat_min_word_num and danmu_count>=self.tl_stat_min_count:
            start_str=getTime(start_ts,fmt="%Y-%m-%d %H:%M:%S")
            duration=(last_ts-start_ts)/60
            records[start_str]="%s,%s,%s,%.1f,%d,%d,%.1f"%(start_str,live_title,liver_name,duration,word_num,danmu_count,word_num/duration)
        try: updateCsvFile("logs/同传数据统计.csv",0,records,2048)
        except UnicodeDecodeError:
            showInfoDialog("CSV文件被其他软件（如Excel）改动后，保存的编码错误\n请尝试将logs目录下的CSV文件移至他处\n"
            +"Excel编码解决方法：微软Excel->设置CSV保存编码为UTF-8\nWPS Excel->安装CoolCsv插件","保存同传统计结果出错")
        except Exception as e:
            logDebug(f"[StatTLRecords] WriteError: ROOMID={roomid} {e}")
        finally:
            return records

    def LogDanmu(self,msg,roomid,src,res,cur_time):
        """输出弹幕发送日志"""
        roomid=str(roomid)
        if roomid in self.danmu_log_dir.keys():
            dir_name=self.danmu_log_dir[roomid]
        else:
            liver_name,_=self.GetLiveInfo(roomid)
            dir_name="%s_%s"%(roomid,liver_name)
            self.danmu_log_dir[roomid]=dir_name
            os.mkdir("logs/danmu/%s"%dir_name)
        try:
            path="logs/danmu/%s/%s.log"%(dir_name,getTime(cur_time,fmt="%y-%m-%d"))
            with open(path,"a",encoding="utf-8") as f:
                f.write("[%d%s][%s]%s\n"%(src,res,getTime(cur_time),msg))
        except Exception as e:
            print("[Log Error]",type(e),e)
        if src==DM_COMMENT and "【" in msg and res=="0":
            if roomid in self.translate_records.keys():
                self.translate_records[roomid][1]=cur_time
            else:
                _,live_title=self.GetLiveInfo(roomid)
                self.translate_records[roomid]=[cur_time,cur_time,live_title]
    
    def LogShielded(self,msg):
        """输出屏蔽词日志"""
        try:
            path="logs/shielded/SHIELDED_%s.log"%getTime(fmt="%y-%m")
            with open(path,"a",encoding="utf-8") as f:
                f.write("%s｜%s\n"%(getTime(fmt="%m-%d %H:%M"),msg))
        except: pass
    
    def LogSongName(self,msg):
        """输出歌词发送日志"""
        try:
            path="logs/lyric/LYRIC_%s.log"%getTime(fmt="%y-%m")
            with open(path,"a",encoding="utf-8") as f:
                f.write("%s｜%s\n"%(getTime(fmt="%m-%d %H:%M"),msg))
        except: pass

    def LoginCheck(self,res):
        """根据接口返回码判断B站账号配置是否有效"""
        if res["code"]==-101 or "登录" in res["message"]:
            self.OnNotLogin()
            return False
        return True
    
    @call_after
    def OnNotLogin(self):
        self.OnStopBtn(None)
        self.ClearQueue(None)
        content="账号未登录\n\nCookie有误或已过期，请重新扫码登录"
        if self.danmuSpreadFrame.StopAll():
            content+="\n已自动暂停弹幕转发"
        showInfoDialog(content,"错误")
        self.ShowGeneralConfigFrame(None)
        self.generalConfigFrame.SelectPage(3)
    
    def SaveAccountInfo(self,acc_no,acc_name,cookie):
        """保存B站账号信息"""
        self.account_names[acc_no]=acc_name
        self.cookies[acc_no]=self.blApi.update_cookie(cookie,acc_no)
        if acc_no==self.cur_acc:
            self.SetTitle("LyricDanmu %s - %s"%(self.LD_VERSION,acc_name))
    
    def SwitchAccount(self,acc_no):
        """切换要使用的B站账号"""
        acc_name=self.account_names[acc_no]
        if acc_no==self.cur_acc:    return
        self.cur_acc=acc_no
        self.SetTitle("LyricDanmu %s - %s"%(self.LD_VERSION,acc_name))
        self.sp_max_len=None
        if self.roomid is not None:
            self.pool.submit(self.ThreadOfGetDanmuConfig)


    def GetLyricData(self,lrcO):
        """将单语歌词字符串整理为歌词数据列表"""
        listO = []
        for o in lrcO.strip().split("\n"):
            for f in splitTnL(o):    listO.append(f)
        return sorted(listO, key=lambda f:f[1])

    def GetMixLyricData(self, lrcO, lrcT):
        """将双语歌词字符串整理为歌词数据列表"""
        dictT,dictO,res = {},{},[]
        for t in lrcT.strip().split("\n"):
            for f in splitTnL(t):    dictT[f[3]]=f
        tempT = sorted(dictT.values(), key=lambda f:f[1])
        for o in lrcO.strip().split("\n"):
            for f in splitTnL(o):    dictO[f[3]]=f
        listO,olen = sorted(dictO.values(), key=lambda f:f[1]),len(dictO)
        td,tlT,tlO = [5]*olen,[None]*olen,[f[1] if f[2]!="" else -5 for f in listO]
        for f in tempT:
            for i in range(olen):
                dif=abs(f[1]-tlO[i])
                if dif<td[i] and listO[i][2]!="":   td[i],tlT[i]=dif,f[3]
        for i in range(olen):
            res.append(listO[i])
            res.append(listO[i] if tlT[i] is None or re.match("不得翻唱|^//$",dictT[tlT[i]][2]) else dictT[tlT[i]])
        return res

    def FilterLyric(self,fs):
        """过滤歌词中的无用信息，并整理空行"""
        res,fslen,prev_empty,i=[],len(fs),False,0
        while i<fslen:
            if re.search(LYRIC_IGNORE_RULES,fs[i][2]):
                i += 2 if self.has_trans else 1
                continue
            if fs[i][2] != "":
                res.append(fs[i])
                prev_empty = False
            else:
                if not prev_empty:
                    res.append(["",fs[i][1],"",""])
                    if self.has_trans:
                        res.append(["",fs[i][1],"",""])
                    prev_empty = True
                i+=1
                continue
            i+=1
            if self.has_trans and i<fslen:
                res.append(fs[i])
                i+=1
        return res

    def MergeSingleLyric(self,fs):
        """对单语歌词进行时轴合并处理"""
        fslen,usedlen=len(fs),len(self.cbbLycPre.GetValue().lstrip())+1
        res,base_tl,prev_tl,content,new_line=[],0,100,"",True
        for i in range(fslen):
            tl,c=fs[i][1],fs[i][2]
            if c=="":   continue
            if tl-prev_tl>=LYRIC_EMPTY_LINE_THRESHOLD_S:
                if not new_line:    res.append([getTimeLineStr(base_tl,1),base_tl,content,""])
                res.append(["",prev_tl+3,"",""])
                new_line=True
            prev_tl=tl
            if new_line:
                base_tl,content,new_line=tl,c,False
                continue
            if tl-base_tl<=self.lyric_merge_threshold_s and len(content+c)+usedlen<=self.max_len:
                content+="　"+c
                continue
            res.append([getTimeLineStr(base_tl,1),base_tl,content,""])
            base_tl,content=tl,c
        if not new_line:    res.append([getTimeLineStr(base_tl,1),base_tl,content,""])
        return res

    def MergeMixLyric(self,fs):
        """对双语歌词进行时轴合并处理"""
        fslen,usedlen=len(fs),len(self.cbbLycPre.GetValue().lstrip())+1
        res,base_tl,prev_tl,content_o,content_t,new_line=[],0,100,"","",True
        for i in range(0,fslen,2):
            tl,co,ct=fs[i+1][1],fs[i][2],fs[i+1][2]
            if ct=="":   continue
            if tl-prev_tl>=LYRIC_EMPTY_LINE_THRESHOLD_S:
                if not new_line:
                    res.append([getTimeLineStr(base_tl,1),base_tl,content_o,""])
                    res.append([getTimeLineStr(base_tl,1),base_tl,content_t,""])
                res.append(["",prev_tl+3,"",""])
                res.append(["",prev_tl+3,"",""])
                new_line=True
            prev_tl=tl
            if new_line:
                base_tl,content_o,content_t,new_line=tl,co,ct,False
                continue
            if tl-base_tl<=self.lyric_merge_threshold_s and len(content_t+ct)+usedlen<=self.max_len:
                content_o,content_t=content_o+"　"+co,content_t+"　"+ct
                continue
            res.append([getTimeLineStr(base_tl,1),base_tl,content_o,""])
            res.append([getTimeLineStr(base_tl,1),base_tl,content_t,""])
            base_tl,content_o,content_t=tl,co,ct
        if not new_line:
            res.append([getTimeLineStr(base_tl,1),base_tl,content_o,""])
            res.append([getTimeLineStr(base_tl,1),base_tl,content_t,""])
        return res

    def RecvLyric(self,data):
        """解析歌词数据并显示在歌词面板"""
        self.init_lock = False
        self.OnStopBtn(None)
        self.sldLrc.Show(True)
        self.has_trans=data["has_trans"]
        self.cur_song_name=data["name"]
        self.has_timeline=True
        so=re.search(r"\[(\d+):(\d+)(\.\d*)?\]",data["lyric"])
        if so is None:
            tmpList=data["lyric"].strip().split("\n")
            tmpData=[["", -1, i.strip(), ""] for i in tmpList]
            self.has_timeline=False
        elif self.has_trans and data["src"]!="local":
            tmpData=self.GetMixLyricData(data["lyric"],data["tlyric"])
        else:
            tmpData=self.GetLyricData(data["lyric"])
        tmpData=self.FilterLyric(tmpData)
        self.lyric_raw="\r\n".join([i[2] for i in tmpData])
        self.lyric_raw_tl="\r\n".join([i[3]+i[2] for i in tmpData])
        if self.has_timeline and self.enable_lyric_merge:
            tmpData=self.MergeMixLyric(tmpData) if self.has_trans else self.MergeSingleLyric(tmpData)
        lyrics="\r\n".join([i[2] for i in tmpData])
        for k, v in HTML_TRANSFORM_RULES.items():
            lyrics = re.sub(k, v, lyrics)
            self.lyric_raw = re.sub(k,v,self.lyric_raw)
            self.lyric_raw_tl = re.sub(k,v,self.lyric_raw_tl)
        lyrics=self.AntiShield(lyrics)
        lyric_list=lyrics.split("\r\n")
        for i in range(len(lyric_list)):
            tmpData[i][2]=lyric_list[i]
        if self.add_song_name and data["name"]!="" and len(tmpData)>0:
            tl=(tmpData[-1][1]+3) if tmpData[-1][1]>=0 else -1
            tl_str=getTimeLineStr(tl,1) if tl>=0 else ""
            name_info=self.AntiShield("歌名："+data["name"])
            tmpData.append(["",tl,"",""])
            tmpData.append([tl_str,tl,name_info,""])
            if self.has_trans:
                tmpData.append([tl_str,tl,name_info,""]) 
        tmpData.insert(0,["",-1,"<BEGIN>",""])
        tmpData.append(["",-1,"<END>",""])
        if self.has_trans:
            tmpData.insert(0,["",-1,"<BEGIN>",""])
            tmpData.append(["",-1,"<END>",""])
        self.llist=tmpData
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
        self.lid = self.olist[self.oid]
        if self.has_trans and self.lyc_mod > 0:
            self.lid += 1
        self.sldLrc.SetRange(0, self.omax - 2)
        self.sldLrc.SetValue(self.oid)
        self.lblCurLine.SetLabel(str(self.oid))
        self.lblMaxLine.SetLabel(str(self.omax - 2))
        self.RefreshLyric()
        self.show_lyric=True
        self.show_import=False
        self.ResizeUI()
        if self.has_timeline:
            self.btnAutoSend.SetLabel("自动 ▶")
            self.btnAutoSend.Enable()
            self.btnStopAuto.Enable()
        else:
            self.btnAutoSend.SetLabel("无时间轴")
            self.btnAutoSend.Disable()
            self.btnStopAuto.Disable()

    def RefreshLyric(self):
        """刷新歌词文本的显示"""
        if self.init_lock:  return
        offset=int(self.has_trans and self.lyc_mod>0) - 4 
        for i in range(11):
            lid = self.olist[self.oid+self.lyric_offset] + i +offset
            if 0 <= lid < self.lmax:
                self.lblTimelines[i].SetLabel(self.llist[lid][0])
                self.lblLyrics[i].SetLabel(self.llist[lid][2])
            else:
                self.lblTimelines[i].SetLabel("")
                self.lblLyrics[i].SetLabel("")


    def CheckFile(self):
        """检查配置文件与数据文件是否存在，若不存在则进行创建"""
        dirs=("songs","logs","logs/danmu","logs/lyric","logs/debug","logs/shielded")
        for dir in dirs:
            if not os.path.exists(dir): os.mkdir(dir)
        if not os.path.exists("config.txt"):
            self.SaveConfig()
        if not os.path.exists("rooms.txt"):
            with open("rooms.txt", "w", encoding="utf-8") as f:     f.write("")
        if not os.path.exists("rooms_spread.txt"):
            op="copy" if self.platform=="win" else "cp"
            os.system(op+" rooms.txt rooms_spread.txt")
        if not os.path.exists("marks_wy.txt"):
            with open("marks_wy.txt", "w", encoding="utf-8") as f:  f.write("")
        if not os.path.exists("marks_qq.txt"):
            with open("marks_qq.txt", "w", encoding="utf-8") as f:  f.write("")
        if not os.path.exists("shields.txt"):
            with open("shields.txt", "w", encoding="utf-8") as f:   f.write("")
        if not os.path.exists("shields_global.dat"):
            with open("shields_global.dat", "w", encoding="utf-8") as f:    f.write("")
        if not os.path.exists("custom_texts.txt"):
            with open("custom_texts.txt", "w", encoding="utf-8") as f:  f.write(DEFAULT_CUSTOM_TEXT)
        if not os.path.exists("logs/recent.dat"):
            with open("logs/recent.dat", "w", encoding="utf-8") as f:   f.write("")
        if not os.path.exists("logs/同传数据统计.csv"):
            with open("logs/同传数据统计.csv", "w", encoding="utf-8-sig") as f:
                f.write("同传开始时间,直播标题,主播,持续时间(分钟),同传字数,同传条数,速度(字/分钟)\n")

    def ReadFile(self):
        """从文件中读取配置与数据"""
        try:
            with open("config.txt", "r", encoding="utf-8") as f:
                for line in f:
                    if "=" not in line:     continue
                    sp = line.split("=", 1)
                    k,v=sp[0].strip().lower(),sp[1].strip()
                    if k == "默认歌词前缀":
                        self.prefix = v
                    elif k == "默认歌词后缀":
                        self.suffix = v
                    elif k == "歌词前缀备选":
                        self.prefixs = v.split(",")
                    elif k == "歌词后缀备选":
                        self.suffixs = v.split(",")
                    elif k == "歌词高亮显示":
                        self.lyric_offset = 0 if "待发送" not in v else 1
                    elif k == "启用歌词合并":
                        self.enable_lyric_merge = v.lower()=="true"
                    elif k == "歌词合并阈值":
                        merge_th = int(v)
                        if 3000 <= merge_th <= 8000:
                            self.lyric_merge_threshold_s=0.001*merge_th
                    elif k == "曲末显示歌名":
                        self.add_song_name = v.lower()=="true"
                    elif k == "最低发送间隔":
                        interval = int(v)
                        if 500 <= interval <= 1500:
                            self.send_interval_ms = interval
                    elif k == "请求超时阈值":
                        tm_out = int(v)
                        if 2000 <= tm_out <= 10000:
                            self.timeout_s=0.001*tm_out
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
                        self.init_show_lyric = v.lower()=="true"
                    elif k == "忽略系统代理":
                        self.no_proxy = v.lower()=="true"
                    elif k == "账号标注":
                        self.account_names[0] = "账号1" if v=="" else v
                    elif k == "账号标注2":
                        self.account_names[1] = "账号2" if v=="" else v
                    elif k == "cookie":
                        self.cookies[0] = v
                    elif k == "cookie2":
                        self.cookies[1] = v
                    elif k == "同传中断阈值":
                        self.tl_stat_break_min = min(max(int(v),5),30)
                    elif k == "最低字数要求":
                        self.tl_stat_min_word_num = max(int(v),0)
                    elif k == "最低条数要求":
                        self.tl_stat_min_count = max(int(v),2)
                    elif k == "退出时显示统计":
                        self.show_stat_on_close = v.lower()=="true"
                    elif k == "默认双前缀模式":
                        self.init_two_prefix = v.lower()=="true"
                    elif k == "默认打开记录":
                        self.init_show_record = v.lower()=="true"
                    elif k == "彩色弹幕记录":
                        self.enable_rich_record = v.lower()=="true"
                    elif k == "弹幕记录字号":
                        self.record_fontsize = min(max(int(v),9),16)
                    elif k == "屏蔽句自动重发": 
                        self.f_resend = v.lower()=="true"
                    elif k == "屏蔽句重发标识":
                        self.f_resend_mark = v.lower()=="true"
                    elif k == "进一步处理屏蔽句":
                        self.f_resend_deal = v.lower()=="true"
                    elif k == "app弹幕置底显示":
                        self.app_bottom_danmu = v.lower()=="true"
                    elif k == "截断发送失败弹幕":
                        self.cancel_danmu_after_failed = v.lower()=="true"
        except Exception:
            return showInfoDialog("读取config.txt失败", "启动出错")
        try:
            with open("rooms.txt", "r", encoding="utf-8") as f:
                for line in f:
                    mo=re.match(r"\s*(\d+)\s+(\S+)",line)
                    if mo is not None:
                        self.rooms[mo.group(1)] = mo.group(2)
        except Exception:
            showInfoDialog("读取rooms.txt失败", "提示")
        try:
            with open("rooms_spread.txt", "r", encoding="utf-8") as f:
                for line in f:
                    mo=re.match(r"\s*(\d+)\s+(\S+)(?:\s+(\S+))?",line)
                    if mo is not None:
                        self.sp_rooms[mo.group(1)] = [mo.group(2),"" if mo.group(3) is None else mo.group(3)]
        except Exception:
            showInfoDialog("读取rooms_spread.txt失败", "提示")
        try:
            with open("marks_wy.txt", "r", encoding="utf-8") as f:
                for line in f:
                    mo = re.match(r"\s*(\d+)\s+(.+)", line)
                    if mo is not None:
                        self.wy_marks[mo.group(1)] = mo.group(2)
        except Exception:
            showInfoDialog("读取marks_wy.txt失败", "提示")
        try:
            with open("marks_qq.txt", "r", encoding="utf-8") as f:
                for line in f:
                    mo = re.match(r"\s*(\d+)\s+(.+)", line)
                    if mo is not None:
                        self.qq_marks[mo.group(1)] = mo.group(2)
        except Exception:
            showInfoDialog("读取marks_qq.txt失败", "提示")
        try:
            with open("shields.txt", "r", encoding="utf-8") as f:
                for line in f:
                    mo = re.match(r"\s*(0|1)\s+(\S+)\s+(\S+)\s*(\S*)", line)
                    if mo is None:  continue
                    if mo.group(1)=="0":
                        so=re.search(r"#[1-9]",mo.group(2))
                        if so is not None:
                            rep=re.sub(r"#([1-9])",lambda x: int(x.group(1))*"`",mo.group(2),count=1)
                            rep=re.sub(r"#[1-9]","",rep)
                        else:   rep=mo.group(2)[0]+"`"+mo.group(2)[1:]
                    else:   rep=mo.group(3).replace("·","`").replace("\\","\\\\")
                    rooms=mo.group(4).strip(",")
                    if mo.group(2) in self.custom_shields.keys(): #合并房间列表
                        old_rooms=self.custom_shields[mo.group(2)][2]
                        rooms=",".join(set((old_rooms+","+rooms).split(","))) if old_rooms!="" and rooms!="" else ""
                    self.custom_shields[mo.group(2)]=[int(mo.group(1)),rep,rooms]
        except Exception:
            showInfoDialog("读取shields.txt失败", "提示")
        try:
            scope= {"modified_time":0,"words":[],"rules":{},"ex_words":[],"ex_rules":{}}
            with open("shields_global.dat","r",encoding="utf-8") as f:
                exec(f.read(),scope)
            self.anti_shield=BiliLiveAntiShield(scope["rules"],scope["words"])
            self.anti_shield_ex=BiliLiveAntiShield(scope["ex_rules"],scope["ex_words"])
            self.need_update_global_shields=time.time()-scope["modified_time"]>GLOBAL_SHIELDS_UPDATE_INTERVAL_S
        except Exception:
            showInfoDialog("读取shields_global.dat失败", "提示")
        try:
            cur_time=int(time.time())
            with open("logs/recent.dat", "r", encoding="utf-8") as f:
                for line in f:
                    mo = re.match(r"(\d+),(\d+),(\d+),(.*)", line)
                    if mo and cur_time-int(mo.group(3))<=self.tl_stat_break_min*60:
                        self.translate_records[mo.group(1)]=[int(mo.group(2)),None,mo.group(4).strip()]
        except Exception:
            showInfoDialog("读取logs/recent.dat失败", "提示")
        # 读取弹幕记录目录名称列表
        for dir_name in os.listdir("logs/danmu"):
            if os.path.isfile("logs/danmu/"+dir_name):    continue
            mo = re.match(r"^(\d+)_.+$",dir_name)
            if mo: self.danmu_log_dir[mo.group(1)]=mo.group()
        self.ReadCustomTexts()
        self.ReadLocalSongs()
        return True

    def ReadCustomTexts(self):
        """加载用户预设文本"""
        default_data={
            "title":"(右键编辑)",
            "content":"",
        }
        try:
            collection = xml.dom.minidom.parse("custom_texts.txt").documentElement
            texts = collection.getElementsByTagName("text")
        except Exception:
            return showInfoDialog("读取custom_texts.txt失败", "提示")
        index=0
        for text in texts:
            data=default_data.copy()
            if text.hasAttribute("title") and text.getAttribute("title").strip()!="":
                data["title"]=text.getAttribute("title")
            data["content"]=text.childNodes[0].data
            self.custom_texts.append(data)
            index+=1
            if index>=4:    break
        while index<4:
            self.custom_texts.append(default_data.copy())
            index+=1

    def ConvertLocalSong(self,filepath):
        '''
        对本地歌词内容进行如下转化：
        1. 对歌词内容中的&<>进行全角替换，避免歌词解析失败
        2. 如果歌词文件无<local>根节点，则添加(处理旧版本歌词格式的遗留问题)
        '''
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content=f.read().strip().replace("&","＆")
            content=re.sub("<(?!/?(?:local|name|artists|tags|type|lyric)>)","＜",content)
            content=re.sub("(?<!ocal|name|ists|tags|type|yric)>","＞",content)
            content="<local>\n"+content+"\n</local>" if re.match("<name>",content) else content
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            return xml.dom.minidom.parseString(content)
        except Exception as e:
            logDebug(f"[ConvertLocalSong] filepath={filepath} {e}")

    def ReadLocalSongs(self):
        """加载本地歌曲"""
        fileList = os.listdir("songs")
        for file in fileList:
            filepath = "songs/" + file
            if not os.path.isfile(filepath):    continue
            DOMTree = None
            try:    DOMTree = xml.dom.minidom.parse(filepath)
            except xml.parsers.expat.ExpatError:
                DOMTree = self.ConvertLocalSong(filepath)
            except Exception as e:
                logDebug(f"[ReadLocalSongs(1)] filepath={filepath} {e}")
            if DOMTree is None:     continue
            try:
                localSong = DOMTree.documentElement
                name=re.sub(r";|；","",getNodeValue(localSong,"name"))
                artists=re.sub(r";|；","/",getNodeValue(localSong,"artists"))
                lang="双语" if getNodeValue(localSong,"type") == "双语" else "单语"
                tags=getNodeValue(localSong,"tags")
                self.locals[file]=name+";"+artists+";"+lang+";"+tags
            except Exception as e:
                logDebug(f"[ReadLocalSongs(2)] filepath={filepath} {e}")

    def CreateLyricFile(self,name,artists,tags,lyric,has_trans):
        """创建本地歌词文件"""
        filename=re.sub(r";|；","",name)
        lang="双语" if has_trans else "单语"
        for k,v in FILENAME_TRANSFORM_RULES.items():
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
                f.write("<local>\n")
                f.write("<name>" + name + "</name>\n")
                f.write("<artists>" + artists + "</artists>\n")
                f.write("<tags>" + tags + "</tags>\n")
                f.write("<type>" + lang + "</type>\n")
                f.write("<lyric>\n" + lyric +"\n</lyric>\n")
                f.write("</local>")
            self.locals[filename+".txt"]=name+";"+artists+";"+lang+";"+tags
            showInfoDialog("歌词保存成功", "提示")
            return True
        except:
            return showInfoDialog("文件写入失败", "歌词保存失败")

    def ShowLocalInfo(self,file):
        """读取本地歌词文件并显示相关信息"""
        try:
            localSong =xml.dom.minidom.parse("songs/"+file).documentElement
            lyric=getNodeValue(localSong,"lyric")
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
            logDebug(f"[ShowLocalInfo] file={file} {e}")
            return False

    def SaveConfig(self):
        """将应用配置写入配置文件config.txt"""
        def titleLine(title): return "%s\n#%s#\n%s\n"%("-"*15,title,"-"*15)
        try:
            with open("config.txt", "w", encoding="utf-8") as f:
                f.write(titleLine("歌词显示配置"))
                f.write("默认歌词前缀=%s\n" % self.prefix)
                f.write("默认歌词后缀=%s\n" % self.suffix)
                f.write("歌词前缀备选=%s\n" % ",".join(self.prefixs))
                f.write("歌词后缀备选=%s\n" % ",".join(self.suffixs))
                f.write("歌词高亮显示=%s\n" % ("当前播放行" if self.lyric_offset==0 else "待发送歌词"))
                f.write("启用歌词合并=%s\n" % self.enable_lyric_merge)
                f.write("歌词合并阈值=%d\n" % int(1000*self.lyric_merge_threshold_s))
                f.write("曲末显示歌名=%s\n" % self.add_song_name)
                f.write(titleLine("歌词搜索配置"))
                f.write("默认搜索来源=%s\n" % ("网易云音乐" if self.default_src=="wy" else "QQ音乐"))
                f.write("歌曲搜索条数=%d\n" % self.search_num)
                f.write("每页显示条数=%d\n" % self.page_limit)
                f.write(titleLine("弹幕发送配置"))
                f.write("忽略系统代理=%s\n" % self.no_proxy)
                f.write("最低发送间隔=%d\n" % self.send_interval_ms)
                f.write("请求超时阈值=%d\n" % int(1000*self.timeout_s))
                f.write("屏蔽句自动重发=%s\n" % self.f_resend)
                f.write("进一步处理屏蔽句=%s\n" % self.f_resend_deal)
                f.write("截断发送失败弹幕=%s\n" % self.cancel_danmu_after_failed)
                f.write("app弹幕置底显示=%s\n" % self.app_bottom_danmu)
                f.write(titleLine("同传统计配置"))
                f.write("同传中断阈值=%d\n" % self.tl_stat_break_min)
                f.write("最低字数要求=%d\n" % self.tl_stat_min_word_num)
                f.write("最低条数要求=%d\n" % self.tl_stat_min_count)
                f.write("退出时显示统计=%s\n" % self.show_stat_on_close)
                f.write(titleLine("弹幕记录配置"))
                f.write("彩色弹幕记录=%s\n" % self.enable_rich_record)
                f.write("弹幕记录字号=%d\n" % self.record_fontsize)
                f.write("屏蔽句重发标识=%s\n" % self.f_resend_mark)
                f.write(titleLine("默认启动配置"))
                f.write("默认展开歌词=%s\n" % self.init_show_lyric)
                f.write("默认打开记录=%s\n" % self.init_show_record)
                f.write("默认双前缀模式=%s\n" % self.init_two_prefix)
                f.write(titleLine("账号信息配置"))
                f.write("账号标注=%s\n" % self.account_names[0])
                f.write("cookie=%s\n" % self.cookies[0])
                f.write("账号标注2=%s\n" % self.account_names[1])
                f.write("cookie2=%s\n" % self.cookies[1])
        except Exception as e:
            logDebug(f"[SaveConfig] {e}")

    def SaveData(self):
        """将数据写入对应的配置文件"""
        try:
            with open("rooms.txt", "w", encoding="utf-8") as f:
                for roomid in self.rooms:
                    f.write("%-15s%s\n" % (roomid, self.rooms[roomid]))
        except: pass
        try:
            with open("rooms_spread.txt", "w", encoding="utf-8") as f:
                for roomid in self.sp_rooms:
                    rname,sname=self.sp_rooms[roomid]
                    room_info=rname+max(19-getStrWidth(rname),1)*" "+sname
                    f.write("%-15s%s\n" % (roomid, room_info))
        except: pass
        try:
            with open("marks_wy.txt", "w", encoding="utf-8") as f:
                for song_id in self.wy_marks:
                    f.write("%-15s%s\n" % (song_id, self.wy_marks[song_id]))
        except: pass
        try:
            with open("marks_qq.txt", "w", encoding="utf-8") as f:
                for song_id in self.qq_marks:
                    f.write("%-15s%s\n" % (song_id, self.qq_marks[song_id]))
        except: pass
        try:
            with open("shields.txt", "w", encoding="utf-8") as f:
                for k,v in self.custom_shields.items():
                    f.write("%d %s %s %s\n" % (v[0],k,v[1].replace("\\\\","\\"),v[2]))
        except: pass
        try:
            with open("custom_texts.txt", "w", encoding="utf-8") as f:
                f.write("<texts>\n")
                for text in self.custom_texts:
                    f.write("<text title=\"%s\">\n%s\n</text>\n"%(text["title"],text["content"].strip()))
                f.write("</texts>")
                f.flush()
        except: pass
