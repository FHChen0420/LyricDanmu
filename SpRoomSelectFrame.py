import wx,re
from LiveUserSearchFrame import LiveUserSearchFrame
from util import showInfoDialog,editDictItem

class SpRoomSelectFrame(wx.Frame):
    def __init__(self, parent, slot, index):
        self.show_pin=parent.show_pin
        self.sp_rooms=parent.sp_rooms
        self.configs=parent.configs
        self.slot=slot
        self.index=index
        self.select=""
        self.disable_rids=[]
        self.liveUserSearchFrame=None
        self.GetDisableList()
        self.ShowFrame(parent)
    
    def ShowFrame(self,parent):
        rowNum=(len(self.sp_rooms))//4+1
        h=110+30*rowNum
        pos,ds=parent.GetPosition(),wx.DisplaySize()
        x,y=pos[0]+20,pos[1]+30
        if y+h>ds[1]:   y=ds[1]-h
        wx.Frame.__init__(self, parent, title="选择直播间 [同传转发]", pos=(x,y), size=(400, h),
            style=wx.DEFAULT_FRAME_STYLE ^ (wx.RESIZE_BORDER | wx.MAXIMIZE_BOX | wx.MINIMIZE_BOX) |wx.FRAME_FLOAT_ON_PARENT)
        if parent.show_pin:
            self.ToggleWindowStyle(wx.STAY_ON_TOP)
        panel=wx.Panel(self,-1)
        self.sbox=wx.StaticBox(panel,-1,"添加房间",pos=(5,h-105),size=(385,73))
        wx.StaticText(panel,-1,"房间号",pos=(10,h-85))
        wx.StaticText(panel,-1,"房间名称",pos=(95,h-85))
        wx.StaticText(panel,-1,"主播简称",pos=(225,h-85))
        wx.StaticText(panel,-1,"单击可编辑房间信息，双击选定房间",pos=(170,h-105)).SetForegroundColour("grey")
        self.tcRoomId=wx.TextCtrl(panel,-1,"",pos=(10,h-65),size=(80,25))
        self.tcRoomName=wx.TextCtrl(panel,-1,"",pos=(95,h-65),size=(98,25),style=wx.TE_PROCESS_ENTER)
        self.tcShortName=wx.TextCtrl(panel,-1,"",pos=(225,h-65),size=(50,25))
        self.btnSearch=wx.Button(panel,-1,"🔍",pos=(195,h-65),size=(25,25))
        self.btnDelete=wx.Button(panel,-1,"删除",pos=(280,h-83),size=(50,43))
        self.btnSelect=wx.Button(panel,-1,"选择",pos=(335,h-83),size=(50,43))
        self.tcRoomName.Bind(wx.EVT_TEXT_ENTER, self.SearchRoom)
        self.btnSearch.Bind(wx.EVT_BUTTON, self.SearchRoom)
        self.btnDelete.Bind(wx.EVT_BUTTON, self.DeleteRoom)
        self.btnSelect.Bind(wx.EVT_BUTTON, self.SaveAndSelectRoom)
        self.btnDelete.Show(False)
        self.tcRoomName.SetFocus()
        i=0
        for roomid,v in self.sp_rooms.items():
            row,col=i//4,i%4
            sname=v[1].replace(";","；")
            btn=wx.Button(panel, -1, v[0], pos=(10+col*95, 5+row*30), size=(90, 27), name=f"{roomid};{sname}")
            if roomid==self.select:
                btn.SetForegroundColour("blue")
                btn.SetFocus()
                self.sbox.SetLabel("编辑房间")
                self.tcRoomId.SetLabel(roomid)
                self.tcRoomName.SetLabel(v[0])
                self.tcShortName.SetLabel(sname)
            if roomid in self.disable_rids:
                btn.SetForegroundColour("grey")
            else:
                btn.Bind(wx.EVT_BUTTON,self.EditRoom)
                btn.Bind(wx.EVT_RIGHT_DOWN,self.EditRoom)
            i+=1
        btnAdd=wx.Button(panel, -1, "✚", pos=(10+i%4*95, 5+i//4*30), size=(90, 27))
        btnAdd.Bind(wx.EVT_BUTTON, self.NewRoom)
        self.Show()
    
    def GetDisableList(self):
        cur_rid=None
        room_lst=self.configs[self.slot][0]
        if self.index==0:
            cur_rid=room_lst[0]
            for cfg in self.configs:
                if cur_rid!=cfg[0][0]:
                    self.disable_rids.append(cfg[0][0])
            for rid in room_lst[1:]:
                self.disable_rids.append(rid)
        else:
            cur_rid=room_lst[self.index] if self.index<len(room_lst) else None
            for rid in room_lst:
                if cur_rid!=rid:
                    self.disable_rids.append(rid)
        self.select="" if cur_rid is None else cur_rid
    
    def NewRoom(self,event):
        if self.select=="": return
        self.select=""
        self.sbox.SetLabel("添加房间")
        self.tcRoomId.Clear()
        self.tcRoomName.Clear()
        self.tcShortName.Clear()
        self.btnDelete.Show(False)
        self.tcRoomName.SetFocus()

    def EditRoom(self,event):
        btnRoom=event.GetEventObject()
        roomid,sname=btnRoom.GetName().split(";")
        if roomid==self.select and isinstance(event,wx.CommandEvent):
            self.SaveAndSelectRoom(None)
            return
        self.select=roomid
        self.sbox.SetLabel("编辑房间")
        self.tcRoomId.SetValue(roomid)
        self.tcRoomName.SetValue(btnRoom.GetLabel())
        self.tcShortName.SetValue(sname)
        self.btnDelete.Show(True)
        btnRoom.SetFocus()
    
    def SaveAndSelectRoom(self,event):
        roomid=self.tcRoomId.GetValue().strip()
        rname=self.tcRoomName.GetValue().strip()
        sname=self.tcShortName.GetValue().strip()
        if roomid=="":
            return showInfoDialog("未填写房间号", "提示")
        if not re.match(r"^\d+$",roomid):
            return showInfoDialog("房间号格式不对", "提示")
        if rname=="":
            return showInfoDialog("未填写房间名称", "提示")
        if sname=="":
            return showInfoDialog("未填写主播简称", "提示")
        if len(sname)>5:
            return showInfoDialog("主播简称过长", "提示")
        if roomid not in self.sp_rooms.keys() and self.select!="":
            self.Parent.Parent.sp_rooms=self.Parent.sp_rooms=self.sp_rooms=\
                editDictItem(self.sp_rooms,self.select,roomid,[rname,sname])
            self.Parent.EditByRoomid(old=self.select,new=roomid)
        else:
            self.sp_rooms[roomid]=[rname,sname]
            self.Parent.SelectRoom(self.slot,self.index,roomid)
        self.Destroy()

    def DeleteRoom(self,event):
        roomid=self.select
        content=f"是否删除房间 {self.sp_rooms[roomid][0]} ({roomid})？"
        dlg = wx.MessageDialog(None, content, "提示", wx.YES_NO|wx.NO_DEFAULT)
        if dlg.ShowModal()==wx.ID_YES:
            self.sp_rooms.pop(roomid)
            self.Parent.UnSelectByRoomid(roomid)
            self.Destroy()
        dlg.Destroy()
    
    def SearchRoom(self,event):
        keyword=self.tcRoomName.GetValue().strip()
        if self.liveUserSearchFrame:
            self.liveUserSearchFrame.Raise()
            self.liveUserSearchFrame.Search(keyword)
        else:
            self.liveUserSearchFrame=LiveUserSearchFrame(self,keyword)
    
    def RecvSearchResult(self,roomid,rname):
        if roomid in self.sp_rooms.keys():
            self.select=roomid
            self.sbox.SetLabel("编辑房间")
            self.tcRoomId.SetValue(roomid)
            self.tcRoomName.SetValue(self.sp_rooms[roomid][0])
            self.tcShortName.SetValue(self.sp_rooms[roomid][1])
            self.btnDelete.Show(True)
        else:
            self.select=""
            self.sbox.SetLabel("新增房间")
            self.tcRoomId.SetValue(roomid)
            self.tcRoomName.SetValue(rname)
            self.tcShortName.SetValue("")
            self.btnDelete.Show(False)