import wx
import pyperclip

class RecordFrame(wx.Frame):
    def __init__(self,parent):
        SW,SH=wx.DisplaySize()
        wx.Frame.__init__(self, parent, title="弹幕发送记录", size=((SW//4,SH//4)), style=wx.DEFAULT_FRAME_STYLE ^ (wx.MAXIMIZE_BOX))
        if parent.show_pin:
            self.ToggleWindowStyle(wx.STAY_ON_TOP)
        self.SetMinSize((SW//5,SH//8))
        self.SetMaxSize((SW//3,SH*4//5))
        self.Bind(wx.EVT_CLOSE,self.OnClose)
        self.tcRecord=wx.TextCtrl(self,-1,"",style=wx.TE_MULTILINE|wx.TE_READONLY)
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
            pyperclip.copy(self.tcRecord.GetValue())
        elif eventId==wx.ID_TOP:
            self.ToggleWindowStyle(wx.STAY_ON_TOP)
