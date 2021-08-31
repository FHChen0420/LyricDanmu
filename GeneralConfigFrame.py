import wx
import os

class GeneralConfigFrame(wx.Frame):
    def __init__(self,parent):
        self.parent=parent
        self.ShowFrame(parent)
    
    def ShowFrame(self,parent):
        pos=parent.GetPosition()
        x,y=pos[0]+70,(pos[1]+40) if parent.show_lyric else (pos[1]-320)
        if y<0: y=0
        wx.Frame.__init__(self, parent, title="应用设置", pos=(x,y), size=(310,405), style=wx.DEFAULT_FRAME_STYLE ^ (wx.RESIZE_BORDER | wx.MAXIMIZE_BOX | wx.MINIMIZE_BOX) |wx.FRAME_FLOAT_ON_PARENT)
        if parent.show_pin:
            self.ToggleWindowStyle(wx.STAY_ON_TOP)
        self.Bind(wx.EVT_CLOSE,self.OnClose)
        panel=wx.Panel(self,-1,pos=(0,0),size=(310,370))
        self.p2=wx.Panel(self,-1,pos=(0,370),size=(310,100))
        # 歌词前后缀
        wx.StaticText(panel,-1,"歌词前缀",pos=(15,10))
        wx.StaticText(panel,-1,"歌词后缀",pos=(15,40))
        wx.StaticText(panel,-1,"默认",pos=(80,10))
        wx.StaticText(panel,-1,"默认",pos=(80,40))
        wx.StaticText(panel,-1,"备选",pos=(160,10))
        wx.StaticText(panel,-1,"备选",pos=(160,40))
        self.tcDfPre=wx.TextCtrl(panel,-1,parent.prefix,pos=(110,8),size=(40,22))
        self.tcDfSuf=wx.TextCtrl(panel,-1,parent.suffix,pos=(110,38),size=(40,22))
        self.tcPreList=wx.TextCtrl(panel,-1,",".join(parent.prefixs),pos=(190,8),size=(100,22))
        self.tcSufList=wx.TextCtrl(panel,-1,",".join(parent.suffixs),pos=(190,38),size=(100,22))
        # 搜索歌词
        wx.StaticText(panel,-1,"歌词搜索",pos=(15,70))
        wx.StaticText(panel,-1,"默认来源",pos=(80,70))
        wx.StaticText(panel,-1,"搜索条数",pos=(80,100))
        wx.StaticText(panel,-1,"每页条数",pos=(195,100))
        self.rdSrcWY=wx.RadioButton(panel,-1,"网易云",pos=(135,70),style=wx.RB_GROUP)
        self.rdSrcQQ=wx.RadioButton(panel,-1,"QQ音乐",pos=(195,70))
        self.rdSrcWY.SetValue(True) if parent.default_src=="wy" else self.rdSrcQQ.SetValue(True)
        wx.StaticText(panel,-1,"⍰",pos=(275,70)).SetToolTip(
            "歌词前后缀备选：使用\",\"分隔各项\n" +
            "歌词搜索条数：范围5~30\n每页显示条数：范围5~8\n\n"+
            "歌词前后缀更改将在工具重启后生效")
        self.tcSearchNum=wx.TextCtrl(panel,-1,str(parent.search_num),pos=(135,98),size=(40,22))
        self.tcPgSize=wx.TextCtrl(panel,-1,str(parent.page_limit),pos=(250,98),size=(40,22))
        # 歌词高亮
        wx.StaticText(panel,-1,"歌词高亮",pos=(15,130))
        self.rdHlCur=wx.RadioButton(panel,-1,"当前播放行",pos=(80,130),style=wx.RB_GROUP)
        self.rdHlNext=wx.RadioButton(panel,-1,"待发送歌词",pos=(170,130))
        self.rdHlCur.SetValue(True) if parent.lyric_offset==0 else self.rdHlNext.SetValue(True)
        # 歌词处理
        wx.StaticText(panel,-1,"歌词处理",pos=(15,160))
        self.ckbLrcMrg = wx.CheckBox(panel,-1,"启用歌词合并", pos=(80,160))
        self.ckbAddSongName = wx.CheckBox(panel,-1,"曲末显示歌名", pos=(180,160))
        wx.StaticText(panel,-1,"⍰",pos=(275,160)).SetToolTip(
            "歌词合并：将短歌词拼接显示并发送，仅对有时轴的歌词生效\n"+
            "合并阈值：合并歌词时，最多允许拼接多少秒以内的歌词\n"+
            "曲末显示歌名：在歌词末尾添加形如“歌名：XXX”的记录")
        wx.StaticText(panel,-1,"合并阈值",pos=(15,186)).SetForegroundColour("gray")
        self.lblLrcMrg = wx.StaticText(panel, -1, "%4.1f s" %(parent.lyric_merge_threshold_s), pos=(240, 184))
        self.sldLrcMrg = wx.Slider(panel, -1, int(10 * parent.lyric_merge_threshold_s), 30, 80, pos=(70, 184), size=(170, 30),style=wx.SL_HORIZONTAL)
        self.ckbLrcMrg.SetValue(parent.enable_lyric_merge)
        self.ckbAddSongName.SetValue(parent.add_song_name)
        self.sldLrcMrg.Bind(wx.EVT_SLIDER, self.OnLrcMergeThChange)
        # 发送间隔
        wx.StaticText(panel,-1,"发送间隔",pos=(15,214))
        self.ckbNewItv = wx.CheckBox(panel,-1,"启用新版发送间隔机制", pos=(80,214))
        self.ckbNewItv.SetValue(parent.enable_new_send_type)
        wx.StaticText(panel,-1,"⍰",pos=(275,214)).SetToolTip(
            "新版：上一条弹幕的响应时刻 → 本条弹幕的发送时刻\n"+
            "旧版：上一条弹幕的发送时刻 → 本条弹幕的发送时刻\n"+
            "推荐间隔：新版700~850，旧版1000~1100")
        self.lblItv = wx.StaticText(panel, -1, "%4d ms" % parent.send_interval_ms, pos=(240, 238))
        self.sldItv = wx.Slider(panel, -1, int(0.1 * parent.send_interval_ms), 50, 150, pos=(70, 238), size=(170, 30),style=wx.SL_HORIZONTAL)
        self.sldItv.Bind(wx.EVT_SLIDER, self.OnIntervalChange)
        # 超时阈值
        wx.StaticText(panel,-1,"超时阈值",pos=(15,268))
        self.lblTmt = wx.StaticText(panel, -1, "%4.1f s" %(parent.timeout_s), pos=(240, 268))
        self.sldTmt = wx.Slider(panel, -1, int(10 * parent.timeout_s), 20, 100, pos=(70, 264), size=(170, 30),style=wx.SL_HORIZONTAL)
        self.sldTmt.Bind(wx.EVT_SLIDER, self.OnTimeoutChange)
        # 其它设置
        wx.StaticText(panel,-1,"默认开启",pos=(15,294))
        self.ckbInitLrc = wx.CheckBox(panel,-1,"歌词面板", pos=(80,294))
        self.ckbInitLrc.SetValue(parent.init_show_lyric)
        self.ckbInitRcd = wx.CheckBox(panel,-1,"弹幕记录", pos=(153,294))
        self.ckbInitRcd.SetValue(parent.init_show_record)
        self.ckbTwoPre = wx.CheckBox(panel,-1,"双前缀", pos=(226,294))
        self.ckbTwoPre.SetValue(parent.init_two_prefix)
        wx.StaticText(panel,-1,"其它设置",pos=(15,319))
        self.ckbNoProxy = wx.CheckBox(panel,-1,"禁用系统代理", pos=(80,319))
        self.ckbNoProxy.SetValue(parent.no_proxy)
        wx.StaticText(panel,-1,"⍰",pos=(275,319)).SetToolTip(
            "默认双前缀模式：默认使用\"\"和\"【\"作为评论可选前缀，推荐同传勾选\n"+
            "禁用系统代理：若科学上网时本工具报网络异常错误，则请尝试勾选")
        # 账号切换
        self.btnAccounts=[]
        wx.StaticText(panel,-1,"账号切换",pos=(15,344))
        for i in range(2):
            acc_name="账号%d"%(i+1) if parent.account_names[i]=="" else parent.account_names[i]
            btn=wx.Button(panel,-1,acc_name,pos=(75+i*90,344),size=(85,22),name=str(i))
            btn.Bind(wx.EVT_BUTTON,self.SwitchAccount)
            btn.Bind(wx.EVT_RIGHT_DOWN,self.ShowCookieEdit)
            self.btnAccounts.append(btn)
        wx.StaticText(panel,-1,"⍰",pos=(275,344)).SetToolTip(
            "左键：切换账号　　右键：修改账号\n"+
            "Cookie获取方法：\n"+
            "电脑浏览器进入直播间 → 按F12打开开发者工具，选择Network栏\n"+
            " → 发送一条弹幕 → Network栏会捕获到名为send的记录\n"+
            " → 点击该记录的Headers栏 → 得到Request Headers中的cookie项\n"+
            " → 粘贴到文本框中并关闭配置窗口\n\n"+
            "如果经常切换B站账号，那么建议使用浏览器无痕模式获取cookie")
        wx.StaticText(self.p2,-1,"账号标记",pos=(15,3)).SetForegroundColour("gray")
        self.tcAccName=wx.TextCtrl(self.p2,-1,"",pos=(75,0),size=(135,22))
        self.btnSaveAcc=wx.Button(self.p2,-1,"保存",pos=(215,0),size=(50,22))
        wx.StaticText(self.p2,-1,"Cookie",pos=(20,35)).SetForegroundColour("gray")
        self.tcCookie=wx.TextCtrl(self.p2,-1,"",pos=(75,26),size=(190,38),style=wx.TE_MULTILINE|wx.TE_PROCESS_ENTER)
        self.tcCookie.Bind(wx.EVT_TEXT_ENTER, self.OnEnter)
        self.btnSaveAcc.Bind(wx.EVT_BUTTON,self.SaveAccountInfo)
        self.p2.Show(False)
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

    def ShowCookieEdit(self,event):
        acc_no=int(event.GetEventObject().GetName())
        self.tcAccName.SetValue(self.parent.account_names[acc_no])
        self.tcCookie.SetValue(self.parent.cookies[acc_no])
        self.p2.Show(True)
        self.SetSize(310,470)
        self.tcCookie.SetFocus()
        self.tcCookie.SelectAll()
        self.btnSaveAcc.SetName(str(acc_no))
    
    def SaveAccountInfo(self,event):
        acc_no=int(event.GetEventObject().GetName())
        acc_name=self.tcAccName.GetValue().strip()
        acc_name="账号%d"%(acc_no+1) if acc_name=="" else acc_name
        cookie=self.tcCookie.GetValue().strip()
        self.btnAccounts[acc_no].SetLabel(acc_name)
        self.parent.SaveAccountInfo(acc_no,acc_name,cookie)
    
    def SwitchAccount(self,event):
        acc_no=int(event.GetEventObject().GetName())
        self.parent.SwitchAccount(acc_no)
        self.OnClose(None)
    
    def OnEnter(self,event):
        pass

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
            if search_num<5:    search_num=5
            if search_num>30:    search_num=30
            parent.search_num=search_num
        except: pass
        try:
            page_limit=int(self.tcPgSize.GetValue().strip())
            if page_limit<5:    page_limit=5
            if page_limit>8:    page_limit=8
            parent.page_limit=page_limit
        except: pass
        parent.lyric_offset=0 if self.rdHlCur.GetValue() else 1
        parent.enable_new_send_type=self.ckbNewItv.GetValue()
        parent.enable_lyric_merge=self.ckbLrcMrg.GetValue()
        parent.add_song_name=self.ckbAddSongName.GetValue()
        parent.init_show_lyric=self.ckbInitLrc.GetValue()
        parent.init_show_record=self.ckbInitRcd.GetValue()
        parent.init_two_prefix=self.ckbTwoPre.GetValue()
        parent.no_proxy=self.ckbNoProxy.GetValue()
        os.environ["NO_PROXY"]="*" if parent.no_proxy else ""
        parent.RefreshLyric()
        if self.parent.customTextFrame:
            self.parent.customTextFrame.RefreshLyric()
        self.Destroy()
