import re

import wx

from frame.liveroom_search import LiveroomSearchFrame
from utils.util import editDictItem, showInfoDialog


class RoomSelectFrame(wx.Frame):
    def __init__(self, parent):
        self.show_pin=parent.show_pin
        self.rooms=parent.rooms
        self.select=""
        self.liveroomSearchFrame=None
        self.ShowFrame(parent)
    
    def ShowFrame(self,parent):
        rowNum=(len(self.rooms))//4+1
        h=110+30*rowNum
        pos,ds=parent.GetPosition(),wx.DisplaySize()
        x,y=pos[0]+20,pos[1]+30
        if y+h>ds[1]:   y=ds[1]-h
        wx.Frame.__init__(self, parent, title="选择直播间", pos=(x,y), size=(400, h),
            style=wx.DEFAULT_FRAME_STYLE ^ (wx.RESIZE_BORDER | wx.MAXIMIZE_BOX | wx.MINIMIZE_BOX) |wx.FRAME_FLOAT_ON_PARENT)
        if parent.show_pin:
            self.ToggleWindowStyle(wx.STAY_ON_TOP)
        panel=wx.Panel(self,-1)
        self.sbox=wx.StaticBox(panel,-1,"添加房间",pos=(5,h-105),size=(385,73))
        wx.StaticText(panel,-1,"房间号",pos=(10,h-85))
        wx.StaticText(panel,-1,"房间名称",pos=(105,h-85))
        wx.StaticText(panel,-1,"左键选定房间，右键可编辑房间信息",pos=(170,h-105)).SetForegroundColour("grey")
        self.tcRoomId=wx.TextCtrl(panel,-1,"",pos=(10,h-65),size=(90,25))
        self.tcRoomName=wx.TextCtrl(panel,-1,"",pos=(105,h-65),size=(118,25),style=wx.TE_PROCESS_ENTER)
        self.btnSearch=wx.Button(panel,-1,"🔍",pos=(225,h-65),size=(25,25))
        self.btnDelete=wx.Button(panel,-1,"删除",pos=(280,h-83),size=(50,43))
        self.btnSelect=wx.Button(panel,-1,"选择",pos=(335,h-83),size=(50,43))
        self.tcRoomName.Bind(wx.EVT_TEXT_ENTER, self.SearchRoom)
        self.btnSearch.Bind(wx.EVT_BUTTON, self.SearchRoom)
        self.btnDelete.Bind(wx.EVT_BUTTON, self.DeleteRoom)
        self.btnSelect.Bind(wx.EVT_BUTTON, self.SaveAndSelectRoom)
        self.btnDelete.Show(False)
        self.tcRoomName.SetFocus()
        i=0
        for roomid,rname in self.rooms.items():
            row,col=i//4,i%4
            btn=wx.Button(panel, -1, rname, pos=(10+col*95, 5+row*30), size=(90, 27), name=roomid)
            btn.Bind(wx.EVT_BUTTON,self.SelectRoom)
            btn.Bind(wx.EVT_RIGHT_DOWN,self.EditRoom)
            if roomid==self.Parent.roomid:
                btn.SetForegroundColour("blue")
                btn.SetFocus()
                self.sbox.SetLabel("编辑房间")
                self.tcRoomId.SetLabel(roomid)
                self.tcRoomName.SetLabel(rname)
                self.select=roomid
            i+=1
        btnAdd=wx.Button(panel, -1, "✚", pos=(10+i%4*95, 5+i//4*30), size=(90, 27))
        btnAdd.Bind(wx.EVT_BUTTON, self.NewRoom)
        self.Show()

    def NewRoom(self,event):
        if self.select=="": return
        self.select=""
        self.sbox.SetLabel("添加房间")
        self.tcRoomId.Clear()
        self.tcRoomName.Clear()
        self.btnDelete.Show(False)
        self.tcRoomName.SetFocus()
    
    def EditRoom(self,event):
        btnRoom=event.GetEventObject()
        roomid,rname=btnRoom.GetName(),btnRoom.GetLabel()
        self.select=roomid
        self.sbox.SetLabel("编辑房间")
        self.tcRoomId.SetValue(roomid)
        self.tcRoomName.SetValue(rname)
        self.btnDelete.Show(True)
        btnRoom.SetFocus()

    def SelectRoom(self,event):
        btnRoom=event.GetEventObject()
        roomid,rname=btnRoom.GetName(),btnRoom.GetLabel()
        self.rooms[roomid]=rname
        self.Parent.EnterRoom(roomid,rname)
        self.Destroy()

    def SaveAndSelectRoom(self,event):
        roomid=self.tcRoomId.GetValue().strip()
        rname=self.tcRoomName.GetValue().strip()
        if roomid=="":
            return showInfoDialog("未填写房间号", "提示")
        if not re.match(r"^\d+$",roomid):
            return showInfoDialog("房间号格式有误", "提示")
        if rname=="":
            return showInfoDialog("未填写房间名称", "提示")
        if len(roomid)<5:
            try:
                data=self.Parent.blApi.get_room_info(roomid,timeout=(1,1))
                actual_roomid=str(data["data"]["room_info"]["room_id"])
                if actual_roomid!=roomid:
                    showInfoDialog(f"检测到短房间号[{roomid}]，已自动获取真实房间号[{actual_roomid}]", "提示")
                    roomid=actual_roomid
            except Exception:
                return showInfoDialog(f"检测到短房间号[{roomid}]，但无法获取真实房间号，请重试\n"+
                "Tip:可在本页面直接搜索主播名称来直接获取真实房间号", "提示")
        if roomid not in self.rooms.keys() and self.select!="":
            self.Parent.rooms=self.rooms=editDictItem(self.rooms,self.select,roomid,rname)
        else:
            self.rooms[roomid]=rname
        self.Parent.EnterRoom(roomid,rname)
        self.Destroy()
    
    def DeleteRoom(self,event):
        roomid=self.select
        content=f"是否删除房间 {self.rooms[roomid]} ({roomid})？"
        dlg = wx.MessageDialog(None, content, "提示", wx.YES_NO|wx.NO_DEFAULT)
        if dlg.ShowModal()==wx.ID_YES:
            self.rooms.pop(roomid)
            if roomid==self.Parent.roomid:
                self.Parent.EnterRoom(None,None)
            self.Parent.roomSelectFrame=RoomSelectFrame(self.Parent)
            self.Destroy()
        dlg.Destroy()

    def SearchRoom(self,event):
        keyword=self.tcRoomName.GetValue().strip()
        if self.liveroomSearchFrame:
            self.liveroomSearchFrame.Raise()
            self.liveroomSearchFrame.Search(keyword)
        else:
            self.liveroomSearchFrame=LiveroomSearchFrame(self,keyword)
    
    def RecvSearchResult(self,roomid,rname):
        if roomid in self.rooms.keys():
            self.select=roomid
            self.sbox.SetLabel("编辑房间")
            self.tcRoomId.SetValue(roomid)
            self.tcRoomName.SetValue(self.rooms[roomid])
            self.btnDelete.Show(True)
        else:
            self.select=""
            self.sbox.SetLabel("新增房间")
            self.tcRoomId.SetValue(roomid)
            self.tcRoomName.SetValue(rname)
            self.btnDelete.Show(False)
