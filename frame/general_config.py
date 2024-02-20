import os

import wx
from pubsub import pub

from const.constant import InternalMessage
from frame.bili_qrcode import BiliQrCodeFrame
from utils.util import bindHint
from utils.controls import AutoPanel

UI_FRAME_MINIMUM_WIDTH = 320
UI_CONTENT_MARGIN_TOP = 12
UI_CONTENT_MARGIN_BOTTOM = 12
UI_CONTENT_ROW_SPACING = 8
UI_CONTENT_ROW_MARGIN = (16, 16) # Left | Right
UI_CONTENT_ROW_TITLE_SPACING = 20
UI_CONTENT_ROW_TITLE_SPACING_SLIDER = 10
UI_CONTENT_ROW_INNER_SPACING = 4


class GeneralConfigFrame(wx.Frame):
    def __init__(self,parent):
        parentCurrentPosition = parent.GetPosition()
        super().__init__(
            parent,
            title = "应用设置",
            pos = (parentCurrentPosition[0] + 70, (parentCurrentPosition[1] + 40 if parent.show_lyric else max(0, parentCurrentPosition[1] - 80))),
            style = wx.DEFAULT_FRAME_STYLE ^ (wx.RESIZE_BORDER | wx.MAXIMIZE_BOX | wx.MINIMIZE_BOX) | wx.FRAME_FLOAT_ON_PARENT,
        )

        class ConfigRow(AutoPanel):
            def __init__(self, parent, title, orient, margin = UI_CONTENT_ROW_MARGIN, titleSpacing = UI_CONTENT_ROW_TITLE_SPACING, innerSpacing = UI_CONTENT_ROW_INNER_SPACING):
                self.__panel = wx.Panel(parent)
                self.__sizer = wx.BoxSizer()
                self.__panel.SetSizer(self.__sizer)

                super().__init__(self.__panel, orient = orient, spacing = innerSpacing)
                self.__sizer.AddSpacer(margin[0])
                self.__sizer.Add(wx.StaticText(self.__panel, -1, title))
                self.__sizer.AddSpacer(titleSpacing)
                self.__sizer.Add(self)
                self.__sizer.AddSpacer(margin[1])

            def Export(self, isFirst = False):
                if isFirst:
                    return (self.__panel, 0)
                return (self.__panel, 0, wx.TOP, UI_CONTENT_ROW_SPACING)
        
        def InitializeDanmuNotebookPage(panel: wx.Panel):
            sizer = wx.BoxSizer(wx.VERTICAL)
            panel.SetSizer(sizer)
            sizer.AddSpacer(UI_CONTENT_MARGIN_TOP)

            # 发送间隔
            row = ConfigRow(panel, "发送间隔", wx.HORIZONTAL, margin = (UI_CONTENT_ROW_MARGIN[0], 0), titleSpacing = UI_CONTENT_ROW_TITLE_SPACING_SLIDER)
            sizer.Add(*row.Export(isFirst = True))
            self.sldItv = row.AddToSizer(wx.Slider(row, -1, int(0.1 * parent.send_interval_ms), 50, 150, size = (170, 26), style = wx.SL_HORIZONTAL))
            self.sldItv.Bind(wx.EVT_SLIDER, self.OnIntervalChange)
            self.lblItv = row.AddToSizer(wx.StaticText(row, -1, "%4d ms" % parent.send_interval_ms, size = (60, 26)))

            # 超时阈值
            row = ConfigRow(panel, "超时阈值", wx.HORIZONTAL, margin = (UI_CONTENT_ROW_MARGIN[0], 0), titleSpacing = UI_CONTENT_ROW_TITLE_SPACING_SLIDER)
            sizer.Add(*row.Export())
            self.sldTmt = row.AddToSizer(wx.Slider(row, -1, int(10 * parent.timeout_s), 20, 100, size = (170, 26), style = wx.SL_HORIZONTAL))
            self.sldTmt.Bind(wx.EVT_SLIDER, self.OnTimeoutChange)
            self.lblTmt = row.AddToSizer(wx.StaticText(row, -1, "%4.1f s" %(parent.timeout_s), size = (60, 26)))

            # 屏蔽句重发
            row = ConfigRow(panel, "屏蔽处理", wx.VERTICAL)
            sizer.Add(*row.Export())
            self.ckbFResend = row.AddToSizer(wx.CheckBox(row,-1,"弹幕被屏蔽时尝试重发"))
            self.ckbFResend.SetValue(parent.f_resend)
            self.ckbFRDeal = row.AddToSizer(wx.CheckBox(row,-1,"重发时进一步处理内容"))
            self.ckbFRDeal.SetValue(parent.f_resend_deal)
            self.ckbFRMark = row.AddToSizer(wx.CheckBox(row,-1,"重发时显示标识"))
            self.ckbFRMark.SetValue(parent.f_resend_mark)

            # 其它设置
            row = ConfigRow(panel, "其它设置", wx.VERTICAL)
            sizer.Add(*row.Export())
            self.ckbCancelSend = row.AddToSizer(wx.CheckBox(row,-1,"长句发送失败时撤回后续内容"))
            self.ckbCancelSend.SetValue(parent.cancel_danmu_after_failed)
            self.ckbAppBottom = row.AddToSizer(wx.CheckBox(row,-1,"APP端弹幕置底显示"))
            self.ckbAppBottom.SetValue(parent.app_bottom_danmu)
            self.ckbNoProxy = row.AddToSizer(wx.CheckBox(row,-1,"禁用系统代理"))
            self.ckbNoProxy.SetValue(parent.no_proxy)
            row.AddToSizerWithoutSpacing(wx.StaticText(row,-1,"若VPN环境下报网络异常，请勾选")).SetForegroundColour("grey")

            sizer.AddSpacer(UI_CONTENT_MARGIN_BOTTOM)
            return panel
        
        def InitializeLyricNotebookPage(panel: wx.Panel):
            sizer = wx.BoxSizer(wx.VERTICAL)
            panel.SetSizer(sizer)
            sizer.AddSpacer(UI_CONTENT_MARGIN_TOP)

            # 歌词前缀
            row = ConfigRow(panel, "歌词前缀", wx.HORIZONTAL)
            sizer.Add(*row.Export(isFirst = True))
            row.AddToSizer(wx.StaticText(row,-1,"默认"))
            self.tcDfPre = row.AddToSizer(wx.TextCtrl(row,-1,parent.prefix,size=(40,22)))
            row.AddToSizer(wx.StaticText(row,-1,"备选"))
            self.tcPreList = row.AddToSizer(wx.TextCtrl(row,-1,",".join(parent.prefixs),size=(100,22)))

            # 歌词后缀
            row = ConfigRow(panel, "歌词后缀", wx.HORIZONTAL)
            sizer.Add(*row.Export())
            row.AddToSizer(wx.StaticText(row,-1,"默认"))
            self.tcDfSuf = row.AddToSizer(wx.TextCtrl(row,-1,parent.suffix,size=(40,22)))
            row.AddToSizer(wx.StaticText(row,-1,"备选"))
            self.tcSufList = row.AddToSizer(wx.TextCtrl(row,-1,",".join(parent.suffixs),size=(100,22)))

            # 搜索歌词
            row = ConfigRow(panel, "歌词搜索", wx.VERTICAL)
            sizer.Add(*row.Export())

            innerRow = AutoPanel(row)
            row.AddToSizer(innerRow, 1, wx.EXPAND)
            innerRow.AddToSizer(wx.StaticText(innerRow,-1,"默认来源"))
            self.rdSrcWY = innerRow.AddToSizer(wx.RadioButton(innerRow,-1,"网易云",style=wx.RB_GROUP))
            self.rdSrcQQ = innerRow.AddToSizer(wx.RadioButton(innerRow,-1,"QQ音乐"))
            self.rdSrcWY.SetValue(True) if parent.default_src=="wy" else self.rdSrcQQ.SetValue(True)
            innerRow.AddToSizer(bindHint(wx.StaticText(innerRow,-1,"[?]"),
                "歌词前后缀备选：使用\",\"分隔各项\n" +
                "歌词搜索条数：范围5~30\n每页显示条数：范围5~8\n \n"
                "歌词前后缀更改将在工具重启后生效"
            ))

            innerRow = AutoPanel(row)
            row.AddToSizer(innerRow, 1, wx.EXPAND)
            innerRow.AddToSizer(wx.StaticText(innerRow,-1,"搜索条数"))
            self.tcSearchNum = innerRow.AddToSizer(wx.TextCtrl(innerRow,-1,str(parent.search_num),size=(40,22)))
            innerRow.AddToSizer(wx.StaticText(innerRow,-1,"每页条数"))
            self.tcPgSize = innerRow.AddToSizer(wx.TextCtrl(innerRow,-1,str(parent.page_limit),size=(40,22)))

            self.ckbNewQQApi = row.AddToSizer(wx.CheckBox(row,-1,"使用新版QQ音乐搜歌接口(需登录)"))
            self.ckbNewQQApi.SetValue(parent.qq_new_api)

            # 歌词高亮
            row = ConfigRow(panel, "歌词高亮", wx.HORIZONTAL)
            sizer.Add(*row.Export())
            self.rdHlCur = row.AddToSizer(wx.RadioButton(row,-1,"当前播放行",style=wx.RB_GROUP))
            self.rdHlNext = row.AddToSizer(wx.RadioButton(row,-1,"待发送歌词"))
            self.rdHlCur.SetValue(True) if parent.lyric_offset==0 else self.rdHlNext.SetValue(True)

            # 歌词处理
            row = ConfigRow(panel, "歌词处理", wx.HORIZONTAL)
            sizer.Add(*row.Export())
            self.ckbLrcMrg = row.AddToSizer(wx.CheckBox(row,-1,"启用歌词合并"))
            self.ckbAddSongName = row.AddToSizer(wx.CheckBox(row,-1,"曲末显示歌名"))
            row.AddToSizer(bindHint(wx.StaticText(row,-1,"[?]"),
                "歌词合并：将短歌词拼接显示并发送，仅对有时轴的歌词生效\n"
                "合并阈值：合并歌词时，最多允许拼接多少秒以内的歌词\n"
                "曲末显示歌名：在歌词末尾添加形如“歌名：XXX”的记录"
            ))
            self.ckbLrcMrg.SetValue(parent.enable_lyric_merge)
            self.ckbAddSongName.SetValue(parent.add_song_name)

            # 合并阈值
            row = ConfigRow(panel, "合并阈值", wx.HORIZONTAL, margin = (UI_CONTENT_ROW_MARGIN[0], 0), titleSpacing = UI_CONTENT_ROW_TITLE_SPACING_SLIDER)
            sizer.Add(*row.Export())
            self.sldLrcMrg = row.AddToSizer(wx.Slider(row, -1, int(10 * parent.lyric_merge_threshold_s), 30, 80, size=(170, 26),style=wx.SL_HORIZONTAL))
            self.sldLrcMrg.Bind(wx.EVT_SLIDER, self.OnLrcMergeThChange)
            self.lblLrcMrg = row.AddToSizer(wx.StaticText(row, -1, "%4.1f s" %(parent.lyric_merge_threshold_s), size = (60, 26)))

            sizer.AddSpacer(UI_CONTENT_MARGIN_BOTTOM)
            return panel
        
        def InitializeUINotebookPage(panel: wx.Panel):
            sizer = wx.BoxSizer(wx.VERTICAL)
            panel.SetSizer(sizer)
            sizer.AddSpacer(UI_CONTENT_MARGIN_TOP)

            # 启动设置
            row = ConfigRow(panel, "启动设置", wx.VERTICAL)
            sizer.Add(*row.Export(isFirst = True))
            self.ckbInitLrc = row.AddToSizer(wx.CheckBox(row,-1,"启动时展开歌词面板"))
            self.ckbInitLrc.SetValue(parent.init_show_lyric)
            self.ckbInitRcd = row.AddToSizer(wx.CheckBox(row,-1,"启动时打开弹幕记录窗口"))
            self.ckbInitRcd.SetValue(parent.init_show_record)
            self.ckbTwoPre = row.AddToSizer(wx.CheckBox(row,-1,"默认在无前缀与【前缀之间切换"))
            self.ckbTwoPre.SetValue(parent.init_two_prefix)

            # 弹幕记录
            row = ConfigRow(panel, "弹幕记录", wx.VERTICAL)
            sizer.Add(*row.Export())

            innerRow = AutoPanel(row)
            row.AddToSizer(innerRow, 1, wx.EXPAND)
            self.ckbRichRcd = innerRow.AddToSizer(wx.CheckBox(innerRow,-1,"彩色提示信息"))
            self.ckbRichRcd.SetValue(parent.enable_rich_record)
            innerRow.AddToSizer(wx.StaticText(innerRow,-1,"字号"))
            self.cbbFontsize = innerRow.AddToSizer(wx.ComboBox(innerRow,-1,size=(40,22),choices=[str(i) for i in range(9,16)],value=str(parent.record_fontsize),style=wx.CB_READONLY))

            row.AddToSizer(wx.StaticText(row,-1,"修改的弹幕记录配置将在重启后生效")).SetForegroundColour("grey")

            # 同传统计
            row = ConfigRow(panel, "同传统计", wx.VERTICAL)
            sizer.Add(*row.Export())
            
            self.ckbStatShow = row.AddToSizer(wx.CheckBox(row,-1,"退出时显示同传弹幕统计"))
            self.ckbStatShow.SetValue(parent.show_stat_on_close)

            innerRow = AutoPanel(row)
            row.AddToSizer(innerRow, 1, wx.EXPAND)
            self.tcStatSuspend = innerRow.AddToSizer(wx.TextCtrl(innerRow,-1,str(parent.tl_stat_break_min),size=(40,22)))
            innerRow.AddToSizer(wx.StaticText(innerRow,-1,"分钟不同传 视为同传结束"))

            innerRow = AutoPanel(row)
            row.AddToSizer(innerRow, 1, wx.EXPAND)
            innerRow.AddToSizer(wx.StaticText(innerRow,-1,"字数要求"))
            self.tcStatWords = innerRow.AddToSizer(wx.TextCtrl(innerRow,-1,str(parent.tl_stat_min_word_num),size=(40,22)))
            innerRow.AddSpacing(8)
            innerRow.AddToSizer(wx.StaticText(innerRow,-1,"弹幕数要求"))
            self.tcStatCount = innerRow.AddToSizer(wx.TextCtrl(innerRow,-1,str(parent.tl_stat_min_count),size=(40,22)))

            row.AddToSizer(wx.StaticText(row,-1,"未达到要求则不纳入同传统计")).SetForegroundColour("grey")

            # 转发设置
            row = ConfigRow(panel, "转发相关", wx.VERTICAL)
            sizer.Add(*row.Export())

            innerRow = AutoPanel(row)
            row.AddToSizer(innerRow, 1, wx.EXPAND)
            innerRow.AddToSizer(wx.StaticText(innerRow, -1, "最大"))
            self.tcSpreadMaximumSpreadRooms = innerRow.AddToSizer(wx.TextCtrl(innerRow, -1, str(parent.spread_maximum_spread_rooms), size=(40,22)))
            innerRow.AddToSizer(wx.StaticText(innerRow, -1, "个转发房间"))
            
            innerRow = AutoPanel(row)
            row.AddToSizer(innerRow, 1, wx.EXPAND)
            innerRow.AddToSizer(wx.StaticText(innerRow, -1, "最大"))
            self.tcSpreadMaximumListenRooms = innerRow.AddToSizer(wx.TextCtrl(innerRow, -1, str(parent.spread_maximum_listen_rooms), size=(40,22)))
            innerRow.AddToSizer(wx.StaticText(innerRow, -1, "个监听房间"))

            row.AddToSizer(wx.StaticText(row,-1,"数量修改后将重置当前转发配置")).SetForegroundColour("grey")
            
            innerRow = AutoPanel(row)
            row.AddToSizer(innerRow, 1, wx.EXPAND)
            self.ckbSpreadLogViewerEnabled = innerRow.AddToSizer(wx.CheckBox(innerRow, -1, "启用转发日志"))
            self.ckbSpreadLogViewerEnabled.SetValue(parent.spread_logviewer_enabled)
            innerRow.AddToSizer(wx.StaticText(innerRow, -1, "高度"))
            self.tcSpreadLogViewerHeight = innerRow.AddToSizer(wx.TextCtrl(innerRow, -1, str(parent.spread_logviewer_height), size=(40,22)))
            
            self.ckbSpreadLogViewerVerbose = row.AddToSizer(wx.CheckBox(row, -1, "详细转发日志"))
            self.ckbSpreadLogViewerVerbose.SetValue(parent.spread_logviewer_verbose)

            sizer.AddSpacer(UI_CONTENT_MARGIN_BOTTOM)
            return panel
        
        def InitializeAccountNotebookPage(panel: wx.Panel):
            self.btnAccSwitches=[]
            self.tcAccNames=[]
            self.tcAccCookies=[]
            self.btnQrLogins=[]
            self.btnAccEdits=[]
            wx.StaticText(panel,-1,"账号切换",pos=(15, 14))
            for i in range(2):
                acc_name="账号%d"%(i+1) if parent.account_names[i]=="" else parent.account_names[i]
                btnAccSwitch=wx.Button(panel,-1,acc_name,pos=(75+i*100, 10),size=(90,25),name=str(i))
                btnAccSwitch.Bind(wx.EVT_BUTTON,self.SwitchAccount)
                wx.StaticText(panel,-1,"账号名称",pos=(15,50+80*i))
                tcAccName=wx.TextCtrl(panel,-1,parent.account_names[i],pos=(75,47+80*i),size=(80,22))
                tcAccName.Disable()
                btnQrLogin=wx.Button(panel,-1,"扫码登录",pos=(160,47+80*i),size=(60,22),name=str(i))
                btnQrLogin.Bind(wx.EVT_BUTTON, self.ShowQrCodeFrame)
                btnAccEdit=wx.Button(panel,-1,"编辑",pos=(225,47+80*i),size=(40,22),name=str(i))
                btnAccEdit.Bind(wx.EVT_BUTTON,self.EditOrSaveAccount)
                wx.StaticText(panel,-1,"Cookie",pos=(20,82+80*i))
                tcAccCookie=wx.TextCtrl(panel,-1,parent.cookies[i],pos=(75,73+80*i),size=(190,38),style=wx.TE_MULTILINE|wx.TE_PROCESS_ENTER)
                tcAccCookie.Bind(wx.EVT_TEXT_ENTER, lambda event: None)
                tcAccCookie.Disable()
                self.btnAccSwitches.append(btnAccSwitch)
                self.tcAccNames.append(tcAccName)
                self.tcAccCookies.append(tcAccCookie)
                self.btnQrLogins.append(btnQrLogin)
                self.btnAccEdits.append(btnAccEdit)
            return panel
        
        self.notebook = wx.Notebook(self)
        self.notebook.AddPage(InitializeDanmuNotebookPage(wx.Panel(self.notebook)), "弹幕", True)
        self.notebook.AddPage(InitializeLyricNotebookPage(wx.Panel(self.notebook)), "歌词")
        self.notebook.AddPage(InitializeUINotebookPage(wx.Panel(self.notebook)), "界面")
        self.notebook.AddPage(InitializeAccountNotebookPage(wx.Panel(self.notebook)), "账号")

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.notebook, 1, wx.EXPAND)
        self.SetSizer(self.sizer)

        self.qrcodeFrame = None
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.FitSizeForContent()
        self.Show()
    
    def FitSizeForContent(self):
        self.Fit()
        currentSize = self.GetSize()
        if currentSize[0] < UI_FRAME_MINIMUM_WIDTH:
            self.SetSize((UI_FRAME_MINIMUM_WIDTH, currentSize[1]))

    def OnIntervalChange(self, event):
        itv = self.sldItv.GetValue()
        self.lblItv.SetLabel("%4d ms" % (itv * 10))
        self.Parent.send_interval_ms = 10 * self.sldItv.GetValue()
    
    def OnTimeoutChange(self, event):
        tmt = self.sldTmt.GetValue()
        self.lblTmt.SetLabel("%4.1f s" % (tmt * 0.1))
        self.Parent.timeout_s = 0.1 * self.sldTmt.GetValue()
        self.Parent.blApi.set_default_timeout(self.Parent.timeout_s)
    
    def OnLrcMergeThChange(self, event):
        mrg = self.sldLrcMrg.GetValue()
        self.lblLrcMrg.SetLabel("%4.1f s" % (mrg * 0.1))
        self.Parent.lyric_merge_threshold_s = 0.1 * self.sldLrcMrg.GetValue()
    
    def EditAccount(self,acc_no):
        self.tcAccNames[acc_no].Enable()
        self.tcAccCookies[acc_no].Enable()
        self.btnAccEdits[acc_no].SetLabel("保存")
    
    def SaveAccount(self,acc_no):
        acc_name=self.tcAccNames[acc_no].GetValue().strip()
        acc_name="账号%d"%(acc_no+1) if acc_name=="" else acc_name
        cookie=self.tcAccCookies[acc_no].GetValue().strip()
        self.btnAccSwitches[acc_no].SetLabel(acc_name)
        self.Parent.SaveAccountInfo(acc_no,acc_name,cookie)
        self.tcAccNames[acc_no].Disable()
        self.tcAccCookies[acc_no].Disable()
        self.btnAccEdits[acc_no].SetLabel("编辑")

    def EditOrSaveAccount(self,event):
        btn = event.GetEventObject()
        acc_no = int(btn.GetName())
        if btn.GetLabel()=="编辑":
            self.EditAccount(acc_no)
        else:
            self.SaveAccount(acc_no)
            
    def SwitchAccount(self,event):
        acc_no=int(event.GetEventObject().GetName())
        self.Parent.SwitchAccount(acc_no)
        self.Close()
    
    def ShowQrCodeFrame(self,event):
        acc_no=int(event.GetEventObject().GetName())
        for btn in self.btnQrLogins:
            btn.Disable()
        self.qrcodeFrame=BiliQrCodeFrame(self,acc_no)

    def SetLoginInfo(self,cookie,acc_no):
        self.tcAccCookies[acc_no].SetValue(cookie)
        self.SaveAccount(acc_no)
        self.Parent.SwitchAccount(acc_no)
    
    def SelectPage(self,page_index):
        self.nb.SetSelection(page_index)

    def OnClose(self,event):
        snapshot = self.Parent.GenerateConfigSnapshot()

        parent=self.Parent
        parent.prefix=self.tcDfPre.GetValue().strip()
        parent.suffix=self.tcDfSuf.GetValue().strip()
        parent.prefixs=self.tcPreList.GetValue().strip().split(",")
        parent.suffixs=self.tcSufList.GetValue().strip().split(",")
        if self.rdSrcWY.GetValue():
            parent.default_src="wy"
            parent.tcSearch.SetName("wy")
            parent.btnSearch.SetName("wy")
            parent.btnSearch2.SetName("qq")
            parent.btnSearch.SetLabel("网易云 ↩")
            parent.btnSearch2.SetLabel("QQ")
        else:
            parent.default_src="qq"
            parent.tcSearch.SetName("qq")
            parent.btnSearch.SetName("qq")
            parent.btnSearch2.SetName("wy")
            parent.btnSearch.SetLabel("QQ ↩")
            parent.btnSearch2.SetLabel("网易云")
        try:
            search_num=int(self.tcSearchNum.GetValue().strip())
            parent.search_num=min(30,max(5,search_num))
        except: pass
        try:
            page_limit=int(self.tcPgSize.GetValue().strip())
            parent.page_limit=min(8,max(5,page_limit))
        except: pass
        try:
            stat_suspend=int(self.tcStatSuspend.GetValue().strip())
            parent.tl_stat_break_min=min(30,max(2,stat_suspend))
        except: pass
        try:
            stat_words=int(self.tcStatWords.GetValue().strip())
            parent.tl_stat_min_word_num=min(1000,max(1,stat_words))
        except: pass
        try:
            stat_count=int(self.tcStatCount.GetValue().strip())
            parent.tl_stat_min_count=min(100,max(1,stat_count))
        except: pass
        parent.lyric_offset=0 if self.rdHlCur.GetValue() else 1
        parent.enable_lyric_merge=self.ckbLrcMrg.GetValue()
        parent.add_song_name=self.ckbAddSongName.GetValue()
        parent.init_show_lyric=self.ckbInitLrc.GetValue()
        parent.init_show_record=self.ckbInitRcd.GetValue()
        parent.init_two_prefix=self.ckbTwoPre.GetValue()
        parent.no_proxy=self.ckbNoProxy.GetValue()
        parent.enable_rich_record=self.ckbRichRcd.GetValue()
        parent.f_resend=self.ckbFResend.GetValue()
        parent.f_resend_deal=self.ckbFRDeal.GetValue()
        parent.f_resend_mark=self.ckbFRMark.GetValue()
        parent.app_bottom_danmu=self.ckbAppBottom.GetValue()
        parent.show_stat_on_close=self.ckbStatShow.GetValue()
        parent.record_fontsize=int(self.cbbFontsize.GetValue())
        parent.cancel_danmu_after_failed=self.ckbCancelSend.GetValue()
        parent.qq_new_api=self.ckbNewQQApi.GetValue()

        # 转发相关
        parent.spread_logviewer_enabled=self.ckbSpreadLogViewerEnabled.GetValue()
        try:
            value=int(self.tcSpreadLogViewerHeight.GetValue().strip())
            parent.spread_logviewer_height=min(3000, max(1, value))
        except: pass
        parent.spread_logviewer_verbose=self.ckbSpreadLogViewerVerbose.GetValue()
        try:
            value=int(self.tcSpreadMaximumSpreadRooms.GetValue().strip())
            parent.spread_maximum_spread_rooms=min(10, max(1, value))
        except: pass
        try:
            value=int(self.tcSpreadMaximumListenRooms.GetValue().strip())
            parent.spread_maximum_listen_rooms=min(20, max(1, value))
        except: pass

        os.environ["NO_PROXY"]="*" if parent.no_proxy else ""
        parent.RefreshLyric()
        if parent.customTextFrame:
            parent.customTextFrame.RefreshLyric()
        if self.qrcodeFrame and not self.qrcodeFrame.cancel:
            self.qrcodeFrame.Close()
        pub.sendMessage(InternalMessage.CORE_CONFIG_UPDATED.value, before = snapshot, after = self.Parent.GenerateConfigSnapshot())
        self.Destroy()
