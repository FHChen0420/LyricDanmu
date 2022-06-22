import wx
import os

from utils.util import showInfoDialog

class GeneralConfigFrame(wx.Frame):
    def __init__(self,parent):
        self.parent=parent
        self.ShowFrame(parent)
    
    def ShowFrame(self,parent):
        pos=parent.GetPosition()
        x,y=pos[0]+70,(pos[1]+40 if parent.show_lyric else max(0,pos[1]-80))
        wx.Frame.__init__(self, parent, title="应用设置", pos=(x,y), size=(310,285), style=wx.DEFAULT_FRAME_STYLE ^ (wx.RESIZE_BORDER | wx.MAXIMIZE_BOX | wx.MINIMIZE_BOX) |wx.FRAME_FLOAT_ON_PARENT)
        if parent.show_pin:
            self.ToggleWindowStyle(wx.STAY_ON_TOP)
        self.Bind(wx.EVT_CLOSE,self.OnClose)
        self.nb=wx.Notebook(self)
        p1=wx.Panel(self.nb)
        p2=wx.Panel(self.nb)
        p3=wx.Panel(self.nb)
        p4=wx.Panel(self.nb)
        ### Tab1 歌词配置
        # 歌词前后缀
        wx.StaticText(p1,-1,"歌词前缀",pos=(15,10))
        wx.StaticText(p1,-1,"歌词后缀",pos=(15,40))
        wx.StaticText(p1,-1,"默认",pos=(80,10))
        wx.StaticText(p1,-1,"默认",pos=(80,40))
        wx.StaticText(p1,-1,"备选",pos=(160,10))
        wx.StaticText(p1,-1,"备选",pos=(160,40))
        self.tcDfPre=wx.TextCtrl(p1,-1,parent.prefix,pos=(110,8),size=(40,22))
        self.tcDfSuf=wx.TextCtrl(p1,-1,parent.suffix,pos=(110,38),size=(40,22))
        self.tcPreList=wx.TextCtrl(p1,-1,",".join(parent.prefixs),pos=(190,8),size=(100,22))
        self.tcSufList=wx.TextCtrl(p1,-1,",".join(parent.suffixs),pos=(190,38),size=(100,22))
        # 搜索歌词
        wx.StaticText(p1,-1,"歌词搜索",pos=(15,70))
        wx.StaticText(p1,-1,"默认来源",pos=(80,70))
        wx.StaticText(p1,-1,"搜索条数",pos=(80,100))
        wx.StaticText(p1,-1,"每页条数",pos=(195,100))
        self.rdSrcWY=wx.RadioButton(p1,-1,"网易云",pos=(135,70),style=wx.RB_GROUP)
        self.rdSrcQQ=wx.RadioButton(p1,-1,"QQ音乐",pos=(195,70))
        self.rdSrcWY.SetValue(True) if parent.default_src=="wy" else self.rdSrcQQ.SetValue(True)
        txtSearchHint = wx.StaticText(p1,-1,"[?]",pos=(272,70))
        txtSearchHint.Bind(wx.EVT_LEFT_DOWN, lambda event: showInfoDialog(
            "歌词前后缀备选：使用\",\"分隔各项\n" +
            "歌词搜索条数：范围5~30\n每页显示条数：范围5~8\n\n"+
            "歌词前后缀更改将在工具重启后生效", "帮助"
        ))
        txtSearchHint.SetForegroundColour("DARK TURQUOISE")
        self.tcSearchNum=wx.TextCtrl(p1,-1,str(parent.search_num),pos=(135,98),size=(40,22))
        self.tcPgSize=wx.TextCtrl(p1,-1,str(parent.page_limit),pos=(250,98),size=(40,22))
        # 歌词高亮
        wx.StaticText(p1,-1,"歌词高亮",pos=(15,130))
        self.rdHlCur=wx.RadioButton(p1,-1,"当前播放行",pos=(80,130),style=wx.RB_GROUP)
        self.rdHlNext=wx.RadioButton(p1,-1,"待发送歌词",pos=(170,130))
        self.rdHlCur.SetValue(True) if parent.lyric_offset==0 else self.rdHlNext.SetValue(True)
        # 歌词处理
        wx.StaticText(p1,-1,"歌词处理",pos=(15,160))
        self.ckbLrcMrg = wx.CheckBox(p1,-1,"启用歌词合并", pos=(80,160))
        self.ckbAddSongName = wx.CheckBox(p1,-1,"曲末显示歌名", pos=(178,160))
        txtLyricHint = wx.StaticText(p1,-1,"[?]",pos=(272,160))
        txtLyricHint.Bind(wx.EVT_LEFT_DOWN, lambda event: showInfoDialog(
            "歌词合并：将短歌词拼接显示并发送，仅对有时轴的歌词生效\n"+
            "合并阈值：合并歌词时，最多允许拼接多少秒以内的歌词\n"+
            "曲末显示歌名：在歌词末尾添加形如“歌名：XXX”的记录", "帮助"
        ))
        txtLyricHint.SetForegroundColour("DARK TURQUOISE")
        wx.StaticText(p1,-1,"合并阈值",pos=(15,190))
        self.lblLrcMrg = wx.StaticText(p1, -1, "%4.1f s" %(parent.lyric_merge_threshold_s), pos=(240, 188))
        self.sldLrcMrg = wx.Slider(p1, -1, int(10 * parent.lyric_merge_threshold_s), 30, 80, pos=(70, 188), size=(170, 30),style=wx.SL_HORIZONTAL)
        self.ckbLrcMrg.SetValue(parent.enable_lyric_merge)
        self.ckbAddSongName.SetValue(parent.add_song_name)
        self.sldLrcMrg.Bind(wx.EVT_SLIDER, self.OnLrcMergeThChange)
        ### Tab2 弹幕配置
        # 发送间隔
        wx.StaticText(p2,-1,"发送间隔",pos=(15,10))
        self.lblItv = wx.StaticText(p2, -1, "%4d ms" % parent.send_interval_ms, pos=(240, 8))
        self.sldItv = wx.Slider(p2, -1, int(0.1 * parent.send_interval_ms), 50, 150, pos=(70, 8), size=(170, 30),style=wx.SL_HORIZONTAL)
        self.sldItv.Bind(wx.EVT_SLIDER, self.OnIntervalChange)
        # 超时阈值
        wx.StaticText(p2,-1,"超时阈值",pos=(15,40))
        self.lblTmt = wx.StaticText(p2, -1, "%4.1f s" %(parent.timeout_s), pos=(240, 38))
        self.sldTmt = wx.Slider(p2, -1, int(10 * parent.timeout_s), 20, 100, pos=(70, 38), size=(170, 30),style=wx.SL_HORIZONTAL)
        self.sldTmt.Bind(wx.EVT_SLIDER, self.OnTimeoutChange)
        # 屏蔽句重发
        wx.StaticText(p2,-1,"屏蔽处理",pos=(15,70))
        self.ckbFResend = wx.CheckBox(p2,-1,"弹幕被屏蔽时尝试重发", pos=(80,70))
        self.ckbFResend.SetValue(parent.f_resend)
        self.ckbFRDeal = wx.CheckBox(p2,-1,"重发时进一步处理内容", pos=(80,92))
        self.ckbFRDeal.SetValue(parent.f_resend_deal)
        self.ckbFRMark = wx.CheckBox(p2,-1,"重发时显示标识", pos=(80,114))
        self.ckbFRMark.SetValue(parent.f_resend_mark)
        # 其它设置
        wx.StaticText(p2,-1,"其它设置",pos=(15,140))
        self.ckbCancelSend = wx.CheckBox(p2,-1,"长句发送失败时撤回后续内容",pos=(80,140))
        self.ckbCancelSend.SetValue(parent.cancel_danmu_after_failed)
        self.ckbAppBottom = wx.CheckBox(p2,-1,"APP端弹幕置底显示", pos=(80,162))
        self.ckbAppBottom.SetValue(parent.app_bottom_danmu)
        self.ckbNoProxy = wx.CheckBox(p2,-1,"禁用系统代理", pos=(80,184))
        self.ckbNoProxy.SetValue(parent.no_proxy)
        wx.StaticText(p2,-1,"若VPN环境下报网络异常，请勾选",pos=(80,200)).SetForegroundColour("grey")
        ### Tab3 界面配置
        # 启动设置
        wx.StaticText(p3,-1,"启动设置",pos=(15,10))
        self.ckbInitLrc = wx.CheckBox(p3,-1,"启动时展开歌词面板", pos=(80,10))
        self.ckbInitLrc.SetValue(parent.init_show_lyric)
        self.ckbInitRcd = wx.CheckBox(p3,-1,"启动时打开弹幕记录窗口", pos=(80,32))
        self.ckbInitRcd.SetValue(parent.init_show_record)
        self.ckbTwoPre = wx.CheckBox(p3,-1,"默认在无前缀与【前缀之间切换", pos=(80,54))
        self.ckbTwoPre.SetValue(parent.init_two_prefix)
        # 弹幕记录
        wx.StaticText(p3,-1,"弹幕记录",pos=(15,85))
        self.ckbRichRcd = wx.CheckBox(p3,-1,"彩色提示信息", pos=(80,85))
        self.ckbRichRcd.SetValue(parent.enable_rich_record)
        wx.StaticText(p3,-1,"字号",pos=(190,85))
        self.cbbFontsize = wx.ComboBox(p3,-1,pos=(220,83),size=(40,22),choices=[str(i) for i in range(9,16)],value=str(parent.record_fontsize),style=wx.CB_READONLY)
        wx.StaticText(p3,-1,"修改的弹幕记录配置将在重启后生效",pos=(80,105)).SetForegroundColour("grey")
        # 同传统计
        wx.StaticText(p3,-1,"同传统计",pos=(15,135))
        self.ckbStatShow = wx.CheckBox(p3,-1,"退出时显示同传弹幕统计", pos=(80,135))
        self.ckbStatShow.SetValue(parent.show_stat_on_close)
        self.tcStatSuspend = wx.TextCtrl(p3,-1,str(parent.tl_stat_break_min),pos=(80,155),size=(40,22))
        wx.StaticText(p3,-1,"分钟不同传 视为同传结束",pos=(122,157))
        wx.StaticText(p3,-1,"字数要求",pos=(80,180))
        self.tcStatWords = wx.TextCtrl(p3,-1,str(parent.tl_stat_min_word_num),pos=(132,178),size=(40,22))
        wx.StaticText(p3,-1,"弹幕数要求",pos=(182,180))
        self.tcStatCount = wx.TextCtrl(p3,-1,str(parent.tl_stat_min_count),pos=(247,178),size=(40,22))
        wx.StaticText(p3,-1,"未达到要求则不纳入同传统计",pos=(80,200)).SetForegroundColour("grey")
        ### Tab4 账号配置
        self.btnAccSwitches=[]
        self.tcAccNames=[]
        self.tcAccCookies=[]
        self.btnAccEdits=[]
        wx.StaticText(p4,-1,"账号切换",pos=(15, 14))
        for i in range(2):
            acc_name="账号%d"%(i+1) if parent.account_names[i]=="" else parent.account_names[i]
            btnAccSwitch=wx.Button(p4,-1,acc_name,pos=(75+i*100, 10),size=(90,25),name=str(i))
            btnAccSwitch.Bind(wx.EVT_BUTTON,self.SwitchAccount)
            wx.StaticText(p4,-1,"账号名称",pos=(15,50+80*i))
            tcAccName=wx.TextCtrl(p4,-1,parent.account_names[i],pos=(75,47+80*i),size=(135,22))
            tcAccName.Disable()
            btnAccEdit=wx.Button(p4,-1,"编辑",pos=(215,47+80*i),size=(50,22),name=str(i))
            btnAccEdit.Bind(wx.EVT_BUTTON,self.EditOrSaveAccount)
            wx.StaticText(p4,-1,"Cookie",pos=(20,82+80*i))
            tcAccCookie=wx.TextCtrl(p4,-1,parent.cookies[i],pos=(75,73+80*i),size=(190,38),style=wx.TE_MULTILINE|wx.TE_PROCESS_ENTER)
            tcAccCookie.Bind(wx.EVT_TEXT_ENTER, lambda event: None)
            tcAccCookie.Disable()
            self.btnAccSwitches.append(btnAccSwitch)
            self.tcAccNames.append(tcAccName)
            self.tcAccCookies.append(tcAccCookie)
            self.btnAccEdits.append(btnAccEdit)
        txtCookieHint = wx.StaticText(p4,-1,"[如何获取Cookie]",pos=(170, 195))
        txtCookieHint.Bind(wx.EVT_LEFT_DOWN, lambda event: showInfoDialog(
            "浏览器进入B站主页，按F12打开开发者工具，选择Network栏\n"+
            "刷新页面，点击被捕获的第一条记录\n"+
            "点击该记录的Headers栏，找到cookie项\n"+
            "复制粘贴到文本框中并关闭配置窗口\n\n"+
            "如果经常切换B站账号，那么建议使用浏览器无痕模式获取cookie",
            "Cookie获取方法"
        ))
        txtCookieHint.SetForegroundColour("DARK TURQUOISE")
        ### 整合
        self.nb.AddPage(p2,"弹幕",True)
        self.nb.AddPage(p1,"歌词")
        self.nb.AddPage(p3,"界面")
        self.nb.AddPage(p4,"账号")
        self.Show()

    def OnIntervalChange(self, event):
        itv = self.sldItv.GetValue()
        self.lblItv.SetLabel("%4d ms" % (itv * 10))
        self.parent.send_interval_ms = 10 * self.sldItv.GetValue()
    
    def OnTimeoutChange(self, event):
        tmt = self.sldTmt.GetValue()
        self.lblTmt.SetLabel("%4.1f s" % (tmt * 0.1))
        self.parent.timeout_s = 0.1 * self.sldTmt.GetValue()
        self.parent.blApi.set_default_timeout(self.parent.timeout_s)
    
    def OnLrcMergeThChange(self, event):
        mrg = self.sldLrcMrg.GetValue()
        self.lblLrcMrg.SetLabel("%4.1f s" % (mrg * 0.1))
        self.parent.lyric_merge_threshold_s = 0.1 * self.sldLrcMrg.GetValue()
    
    def EditOrSaveAccount(self,event):
        btn:wx.Button = event.GetEventObject()
        acc_no=int(btn.GetName())
        if btn.GetLabel()=="编辑":
            self.tcAccNames[acc_no].Enable()
            self.tcAccCookies[acc_no].Enable()
            btn.SetLabel("保存")
        else:
            acc_name=self.tcAccNames[acc_no].GetValue().strip()
            acc_name="账号%d"%(acc_no+1) if acc_name=="" else acc_name
            cookie=self.tcAccCookies[acc_no].GetValue().strip()
            self.btnAccSwitches[acc_no].SetLabel(acc_name)
            self.parent.SaveAccountInfo(acc_no,acc_name,cookie)
            self.tcAccNames[acc_no].Disable()
            self.tcAccCookies[acc_no].Disable()
            btn.SetLabel("编辑")
            
    def SwitchAccount(self,event):
        acc_no=int(event.GetEventObject().GetName())
        self.parent.SwitchAccount(acc_no)
        self.OnClose(None)

    def OnClose(self,event):
        parent=self.parent
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
        os.environ["NO_PROXY"]="*" if parent.no_proxy else ""
        parent.RefreshLyric()
        if self.parent.customTextFrame:
            self.parent.customTextFrame.RefreshLyric()
        self.Destroy()
