import wx
import re
import os

class GeneralConfigFrame(wx.Frame):
    def __init__(self,parent):
        self.parent=parent
        self.ShowFrame(parent)
    
    def ShowFrame(self,parent):
        pos=parent.GetPosition()
        x=pos[0]+70
        y=pos[1]+60
        wx.Frame.__init__(self, parent, title="应用设置", pos=(x,y), size=(310,379), style=wx.DEFAULT_FRAME_STYLE ^ (wx.RESIZE_BORDER | wx.MAXIMIZE_BOX | wx.MINIMIZE_BOX) |wx.FRAME_FLOAT_ON_PARENT)
        if parent.show_pin:
            self.ToggleWindowStyle(wx.STAY_ON_TOP)
        self.Bind(wx.EVT_CLOSE,self.OnClose)
        panel=wx.Panel(self,-1,size=(310,434))
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
        self.rdSrcWY=wx.RadioButton(panel,-1,"网易云",pos=(135,70),style=0)
        self.rdSrcQQ=wx.RadioButton(panel,-1,"QQ音乐",pos=(195,70),style=0)
        self.rdSrcWY.SetValue(True) if parent.default_src=="wy" else self.rdSrcQQ.SetValue(True)
        wx.StaticText(panel,-1,"⍰",pos=(275,70)).SetToolTip(
            "歌词前后缀备选：使用\",\"分隔各项\n" +
            "歌词搜索条数：范围5~30\n每页显示条数：范围5~8\n\n"+
            "歌词前后缀更改将在工具重启后生效")
        self.tcSearchNum=wx.TextCtrl(panel,-1,str(parent.search_num),pos=(135,98),size=(40,22))
        self.tcPgSize=wx.TextCtrl(panel,-1,str(parent.page_limit),pos=(250,98),size=(40,22))
        # 歌词合并
        wx.StaticText(panel,-1,"歌词合并",pos=(15,130))
        self.ckbLrcMrg = wx.CheckBox(panel,-1,"启用歌词合并", pos=(80,130))
        self.ckbLrcMrg.SetValue(parent.enable_lyric_merge)
        wx.StaticText(panel,-1,"⍰",pos=(275,130)).SetToolTip(
            "将零碎的短歌词拼接显示并发送，减少歌词弹幕发送数量\n"+
            "仅对有时轴的歌词生效，合并双语歌词时以中文长度为基准\n"+
            "合并阈值：合并歌词时，最多允许拼接多少秒以内的歌词")
        self.lblLrcMrg = wx.StaticText(panel, -1, "%4.1f s" %(parent.lyric_merge_threshold_s), pos=(240, 154))
        self.sldLrcMrg = wx.Slider(panel, -1, int(10 * parent.lyric_merge_threshold_s), 30, 80, pos=(70, 154), size=(170, 30),style=wx.SL_HORIZONTAL)
        self.sldLrcMrg.Bind(wx.EVT_SLIDER, self.OnLrcMergeThChange)
        # 发送间隔
        wx.StaticText(panel,-1,"发送间隔",pos=(15,184))
        self.ckbNewItv = wx.CheckBox(panel,-1,"启用新版发送间隔机制", pos=(80,184))
        self.ckbNewItv.SetValue(parent.enable_new_send_type)
        wx.StaticText(panel,-1,"⍰",pos=(275,184)).SetToolTip(
            "新版：上一条弹幕的响应时刻 → 本条弹幕的发送时刻\n"+
            "旧版：上一条弹幕的发送时刻 → 本条弹幕的发送时刻\n"+
            "推荐间隔：新版700~850，旧版1000~1100")
        self.lblItv = wx.StaticText(panel, -1, "%4d ms" % parent.send_interval_ms, pos=(240, 208))
        self.sldItv = wx.Slider(panel, -1, int(0.1 * parent.send_interval_ms), 50, 150, pos=(70, 208), size=(170, 30),style=wx.SL_HORIZONTAL)
        self.sldItv.Bind(wx.EVT_SLIDER, self.OnIntervalChange)
        # 超时阈值
        wx.StaticText(panel,-1,"超时阈值",pos=(15,238))
        self.lblTmt = wx.StaticText(panel, -1, "%4.1f s" %(parent.timeout_s), pos=(240, 238))
        self.sldTmt = wx.Slider(panel, -1, int(10 * parent.timeout_s), 20, 100, pos=(70, 234), size=(170, 30),style=wx.SL_HORIZONTAL)
        self.sldTmt.Bind(wx.EVT_SLIDER, self.OnTimeoutChange)
        # 其它设置
        wx.StaticText(panel,-1,"其它设置",pos=(15,264))
        self.ckbInitLrc = wx.CheckBox(panel,-1,"启动时展开歌词面板", pos=(80,264))
        self.ckbInitLrc.SetValue(parent.init_show_lyric)
        self.ckbNoProxy = wx.CheckBox(panel,-1,"不使用系统代理", pos=(80,289))
        self.ckbNoProxy.SetValue(parent.no_proxy)
        wx.StaticText(panel,-1,"⍰",pos=(275,289)).SetToolTip(
            "科学上网时使用本工具可能会报网络异常错误\n"+
            "如果遇到此情况请尝试修改该选项")
        # 账号配置
        wx.StaticText(panel,-1,"账号配置",pos=(15,314))
        self.tcCookie=wx.TextCtrl(panel,-1,parent.cookie,pos=(78,314),size=(190,75),style=wx.TE_MULTILINE|wx.TE_PROCESS_ENTER)
        self.btnEditCookie=wx.Button(panel,-1,"修改Cookie",pos=(80,314),size=(80,22))
        wx.StaticText(panel,-1,"⍰",pos=(275,314)).SetToolTip(
            "Cookie获取方法：\n"+
            "电脑浏览器进入直播间 → 按F12打开开发者工具，选择Network栏\n"+
            " → 发送一条弹幕 → Network栏会捕获到名为send的记录\n"+
            " → 点击该记录的Headers栏 → 得到Request Headers中的cookie项\n"+
            " → 粘贴到文本框中并关闭配置窗口\n\n"+
            "如果经常切换B站账号，那么建议使用浏览器无痕模式获取cookie")
        self.tcCookie.Show(False)
        self.tcCookie.Bind(wx.EVT_TEXT_ENTER, self.OnEnter)
        self.btnEditCookie.Bind(wx.EVT_BUTTON,self.ShowCookieEdit)
        self.Show()

    def OnIntervalChange(self, event):
        itv = self.sldItv.GetValue()
        self.lblItv.SetLabel("%4d ms" % (itv * 10))
        self.parent.send_interval_ms = 10 * self.sldItv.GetValue()
    
    def OnTimeoutChange(self, event):
        tmt = self.sldTmt.GetValue()
        self.lblTmt.SetLabel("%4.1f s" % (tmt * 0.1))
        self.parent.timeout_s = 0.1 * self.sldTmt.GetValue()
    
    def OnLrcMergeThChange(self, event):
        mrg = self.sldLrcMrg.GetValue()
        self.lblLrcMrg.SetLabel("%4.1f s" % (mrg * 0.1))
        self.parent.lyric_merge_threshold_s = 0.1 * self.sldLrcMrg.GetValue()

    def ShowCookieEdit(self,event):
        self.btnEditCookie.Show(False)
        self.SetSize((310,426))
        self.tcCookie.Show(True)
        self.tcCookie.SetFocus()
        self.tcCookie.SelectAll()
    
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
        except:
            pass
        try:
            page_limit=int(self.tcPgSize.GetValue().strip())
            if page_limit<5:    page_limit=5
            if page_limit>8:    page_limit=8
            parent.page_limit=page_limit
        except:
            pass
        parent.enable_new_send_type=self.ckbNewItv.GetValue()
        parent.enable_lyric_merge=self.ckbLrcMrg.GetValue()
        parent.init_show_lyric=self.ckbInitLrc.GetValue()
        parent.no_proxy=self.ckbNoProxy.GetValue()
        os.environ["NO_PROXY"]="*" if parent.no_proxy else ""
        parent.cookie=self.tcCookie.GetValue().strip()
        parent.cookies["Cookie"]=parent.cookie
        so = re.search(r"bili_jct=([0-9a-f]+);?", parent.cookie)
        if so is not None:
            parent.csrf = so.group(1)
            parent.data_SendDanmu["csrf"]=parent.csrf
            parent.data_SendDanmu["csrf_token"]=parent.csrf
            parent.data_SetDanmuCfg["csrf"]=parent.csrf
            parent.data_SetDanmuCfg["csrf_token"]=parent.csrf
        self.Destroy()
