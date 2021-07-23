import wx
import re

class RoomSelectFrame(wx.Frame):
    def __init__(self, parent):
        self.parent=parent
        self.show_extend=False
        self.ShowFrame(parent)
    
    def ShowFrame(self,parent):
        rowNum=len(self.parent.rooms)//4+1
        self.height=h=35+30*rowNum
        pos,ds=parent.GetPosition(),wx.DisplaySize()
        x,y=pos[0]+20,pos[1]+30
        if y+h>ds[1]:   y=ds[1]-h
        wx.Frame.__init__(self, parent, title="选择直播间", pos=(x,y), size=(400, h),
                          style=wx.DEFAULT_FRAME_STYLE ^ (wx.RESIZE_BORDER | wx.MAXIMIZE_BOX | wx.MINIMIZE_BOX) |wx.FRAME_FLOAT_ON_PARENT)
        if parent.show_pin:
            self.ToggleWindowStyle(wx.STAY_ON_TOP)
        panel=wx.Panel(self,-1)
        wx.StaticText(panel,-1,"房间号",pos=(10,h-21))
        wx.StaticText(panel,-1,"标注",pos=(152,h-21))
        self.tcRoomId=wx.TextCtrl(panel,-1,"",pos=(50,h-25),size=(90,27))
        self.tcRoomName=wx.TextCtrl(panel,-1,"",pos=(180,h-25),size=(90,27))
        btnGoto=wx.Button(panel,-1,"进入",pos=(280,h-25),size=(50,27))
        btnSave=wx.Button(panel,-1,"保存",pos=(335,h-25),size=(50,27))
        btnGoto.Bind(wx.EVT_BUTTON, self.GotoRoom)
        btnSave.Bind(wx.EVT_BUTTON, self.GotoRoom)
        unsaved_roomid=True
        i=0
        for k,v in self.parent.rooms.items():
            row,col=i//4,i%4
            btn=wx.Button(panel, -1, v, pos=(10+col*95, 5+row*30), size=(90, 27), name=k)
            btn.Bind(wx.EVT_BUTTON,self.SelectRoom)
            btn.Bind(wx.EVT_RIGHT_DOWN,self.OnRightClick)
            if k==self.parent.roomid:
                btn.SetForegroundColour("BLUE")
                btn.SetFocus()
                unsaved_roomid=False
            i+=1
        btnAdd=wx.Button(panel, -1, "✚", pos=(10+i%4*95, 5+i//4*30), size=(90, 27))
        btnAdd.Bind(wx.EVT_BUTTON, self.Extend)
        if self.parent.roomid is not None:
            self.tcRoomId.SetValue(self.parent.roomid)
            if unsaved_roomid:
                btnAdd.SetForegroundColour("BLUE")
                btnAdd.SetFocus()
        self.Show()

    def Extend(self,event):
        if self.show_extend:    return
        self.SetSize(400,self.height+40)
        self.show_extend=True

    def OnRightClick(self,event):
        dlg = wx.MessageDialog(None, "是否删除房间？", "提示", wx.YES_NO|wx.NO_DEFAULT)
        if dlg.ShowModal()==wx.ID_YES:
            roomid=event.GetEventObject().GetName()
            self.parent.rooms.pop(roomid)
            self.parent.roomSelectFrame=RoomSelectFrame(self.parent)
            self.Destroy()
        dlg.Destroy()

    def SelectRoom(self,event):
        btn=event.GetEventObject()
        self.parent.SetRoomid(btn.GetName(),btn.GetLabel())
        self.Destroy()

    def GotoRoom(self,event):
        roomid=self.tcRoomId.GetValue().strip()
        name=self.tcRoomName.GetValue().strip()
        op=event.GetEventObject().GetLabel()
        if not re.match(r"^\d+$",roomid):
            dlg = wx.MessageDialog(None, "房间号格式不对", "房间信息出错", wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
            return
        if name=="":
            if op=="保存":
                dlg = wx.MessageDialog(None, "房间标注不能为空", "房间信息出错", wx.OK)
                dlg.ShowModal()
                dlg.Destroy()
                return
            name=self.parent.rooms[roomid] if roomid in self.parent.rooms.keys() else roomid
        if op=="保存":
            self.parent.rooms[roomid]=name
        self.parent.SetRoomid(roomid,name)
        self.Destroy()