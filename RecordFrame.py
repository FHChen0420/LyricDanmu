import wx
from util import setFont,wxCopy

class RecordFrame(wx.Frame):
    def __init__(self,parent):
        SW,SH=wx.DisplaySize()
        wx.Frame.__init__(self, parent, title="弹幕发送记录", size=((SW//4,SH//4)), style=wx.DEFAULT_FRAME_STYLE)
        if parent.show_pin:
            self.ToggleWindowStyle(wx.STAY_ON_TOP)
        self.SetMinSize((SW//5,SH//8))
        self.SetMaxSize((SW//3,SH*4//5))
        self.Bind(wx.EVT_CLOSE,self.OnClose)
        self.rich=parent.enable_rich_record
        tc_style=wx.TE_MULTILINE|wx.TE_READONLY
        if self.rich:   tc_style|=wx.TE_RICH2
        self.tcRecord=wx.TextCtrl(self,style=tc_style)
        font_name="微软雅黑" if parent.platform=="win" else None
        setFont(self.tcRecord,parent.record_fontsize,name=font_name)
        self.style:wx.TextAttr=self.tcRecord.GetDefaultStyle()
        menuBar = wx.MenuBar()
        menu = wx.Menu()
        menuBar.Append(menu,"　操作　")
        menu.Append(wx.ID_COPY,"复制全部","")
        menu.Append(wx.ID_CLEAR,"清空记录","")
        menu.Append(wx.ID_TOP,"置顶窗口","",wx.ITEM_CHECK)
        menu.Append(wx.ID_CLOSE,"关闭窗口\tEsc","")
        menu.Check(wx.ID_TOP,parent.show_pin)
        self.SetMenuBar(menuBar)
        self.Bind(wx.EVT_MENU, self.MenuHandler)

    def OnClose(self,event):
        self.Show(False)

    def MenuHandler(self,event):
        eventId=event.GetId()
        if eventId==wx.ID_CLOSE:
            self.OnClose(None)
        elif eventId==wx.ID_CLEAR:
            self.tcRecord.Clear()
        elif eventId==wx.ID_COPY:
            wxCopy(self.tcRecord.GetValue())
        elif eventId==wx.ID_TOP:
            self.ToggleWindowStyle(wx.STAY_ON_TOP)
    
    def AppendText(self,content,color="black"):
        if self.rich:
            self.style.SetTextColour(color)
            self.tcRecord.SetDefaultStyle(self.style)
        self.tcRecord.AppendText(content)

