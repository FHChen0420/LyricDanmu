import wx
from BiliLiveShieldWords import deal

class CustomTextFrame(wx.Frame):
    def __init__(self,parent):
        self.parent=parent
        self.ShowFrame(parent)
        self.RecvLyric(parent.custom_texts[0])
    
    def ShowFrame(self,parent):
        pos=parent.GetPosition()
        x=pos[0]
        y=pos[1]+190
        wx.Frame.__init__(self, parent, title="预设文本", pos=(x,y), size=(450,170), style=wx.DEFAULT_FRAME_STYLE^ (wx.RESIZE_BORDER|wx.MAXIMIZE_BOX|wx.MINIMIZE_BOX)|wx.FRAME_FLOAT_ON_PARENT)
        if parent.show_pin:
            self.ToggleWindowStyle(wx.STAY_ON_TOP)
        self.p1=wx.Panel(self,-1,pos=(0,0),size=(450,170))
        self.p2=wx.Panel(self,-1,pos=(0,0),size=(450,170))
        # P1
        # 预设选择按钮
        self.select_buttons=[]
        for i in range(4):
            btn=wx.Button(self.p1,-1,parent.custom_texts[i]["title"],pos=(5+93*i,5),size=(88,28),name=str(i))
            btn.Bind(wx.EVT_BUTTON,self.FetchLyric)
            btn.Bind(wx.EVT_RIGHT_DOWN,self.ShowEditPanel)
            self.select_buttons.append(btn)
        # 歌词文本
        self.lblLyrics = []
        for i in range(5):
            lyric_content = wx.StaticText(self.p1, -1, "", pos=(5, 40+20 * i), size=(370, 19), style=wx.ALIGN_CENTER | wx.ST_NO_AUTORESIZE)
            self.lblLyrics.append(lyric_content)
        self.lblLyrics[1].SetForegroundColour("blue")
        # 操作按钮
        self.btnPrev=wx.Button(self.p1,-1,"▲",pos=(382, 5), size=(49, 35))
        self.btnNext=wx.Button(self.p1,-1,"▼",pos=(382, 40), size=(49, 35))
        self.btnSend=wx.Button(self.p1,-1,"发送",pos=(382, 83), size=(49, 52))
        self.btnPrev.Bind(wx.EVT_BUTTON, self.PrevLyric)
        self.btnNext.Bind(wx.EVT_BUTTON, self.NextLyric)
        self.btnSend.Bind(wx.EVT_BUTTON, self.OnSendLrcBtn)
        # P2
        # 返回与保存按钮
        self.btnCancel=wx.Button(self.p2,-1,"◀   取  消  ", pos=(15,5), size=(90,30))
        self.btnSave=wx.Button(self.p2,-1,"保   存", pos=(340,5), size=(90,30))
        self.btnCancel.Bind(wx.EVT_BUTTON,self.Cancel)
        self.btnSave.Bind(wx.EVT_BUTTON,self.Save)
        # 输入框
        wx.StaticText(self.p2,-1,"标题",pos=(140,11))
        self.tcTitle=wx.TextCtrl(self.p2,-1,"", pos=(170,6), size=(120,28))
        self.tcContent=wx.TextCtrl(self.p2,-1,"", pos=(15,43), size=(415,92), style=wx.TE_MULTILINE)
        #
        self.btnSend.SetFocus()
        self.p1.Show(True)
        self.p2.Show(False)
        self.Show()
    
    def FetchLyric(self,event):
        index=int(event.GetEventObject().GetName())
        self.RecvLyric(self.parent.custom_texts[index])

    def RecvLyric(self,data):
        content=data["content"].strip()
        # NOTE
        content=deal(content,self.parent.global_shields)
        self.llist=[line for line in content.split("\n") if line.strip()!=""]
        self.llist.insert(0,"<BEGIN>")
        self.llist.append("<END>")
        self.lmax=len(self.llist)
        self.lid=0
        self.FlashLyric()

    def FlashLyric(self):
        for i in range(5):
            lid = self.lid + i - 1
            if lid >= 0 and lid < self.lmax:
                self.lblLyrics[i].SetLabel(self.llist[lid])
            else:
                self.lblLyrics[i].SetLabel("")
    
    def PrevLyric(self, event):
        if self.lid <= 0:
            return False
        self.lid-=1
        self.FlashLyric()
        return True

    def NextLyric(self, event):
        if self.lid >= self.lmax-2:
            return False
        self.lid+=1
        self.FlashLyric()
        return True
    
    def OnSendLrcBtn(self,event):
        parent=self.parent
        if parent.roomid is None:
            dlg = wx.MessageDialog(None, "未指定直播间", "提示", wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
            return
        if not self.NextLyric(None):
            return
        pre = "【"
        suf = "】"
        msg = pre + self.lblLyrics[1].GetLabel()
        msg = parent.DealWithCustomShields(msg)
        parent.SendSplitDanmu(msg,pre,suf)
    
    def ShowEditPanel(self,event):
        index=int(event.GetEventObject().GetName())
        self.btnSave.SetName(str(index))
        title=self.parent.custom_texts[index]["title"].strip()
        title="" if title=="(右键编辑)" else title
        self.tcTitle.SetValue(title)
        self.tcContent.SetValue(self.parent.custom_texts[index]["content"].strip())
        self.p1.Show(False)
        self.p2.Show(True)
    
    def Cancel(self,event):
        self.p2.Show(False)
        self.p1.Show(True)
    
    def Save(self,event):
        index=int(event.GetEventObject().GetName())
        title=self.tcTitle.GetValue().strip()
        title="(右键编辑)" if title=="" else title
        self.parent.custom_texts[index]["title"]=title
        self.parent.custom_texts[index]["content"]=self.tcContent.GetValue().strip()
        self.select_buttons[index].SetLabel(title)
        self.RecvLyric(self.parent.custom_texts[index])
        self.p2.Show(False)
        self.p1.Show(True)