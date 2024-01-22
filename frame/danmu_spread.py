import re

import wx

from frame.spread_room_select import SpRoomSelectFrame
from utils.live_websocket import BiliLiveWebSocket
from utils.util import UIChange
from const.constant import SPREAD_MAXIMUM_LISTEN_ROOMS,SPREAD_MAXIMUM_SPREAD_ROOMS

class DanmuSpreadFrame(wx.Frame):
    def __init__(self, parent):
        self.configs=parent.sp_configs # 每项为[房间号列表,转发开关,限定前缀列表,转发延时列表]
        self.sp_rooms=parent.sp_rooms
        self.websockets=parent.ws_dict
        self.show_pin=parent.show_pin
        self.roomSelector=None
        self.spreadFilter=None
        self.succ_count=0
        self.fail_count=0
        self.ShowFrame(parent)
    
    def ShowFrame(self,parent):
        wx.Frame.__init__(self, parent, title="弹幕转发配置",size=(420,315),
            style=wx.DEFAULT_FRAME_STYLE ^ (wx.RESIZE_BORDER | wx.MAXIMIZE_BOX | wx.MINIMIZE_BOX))
        if parent.show_pin:
            self.ToggleWindowStyle(wx.STAY_ON_TOP)
        self.panel=panel=wx.Panel(self,-1,pos=(0,0),size=(420,315))
        self.btnRoomLst=[]
        self.lblFilterLst=[]
        self.btnCtrlLst=[]
        self.boxLst=[]
        self.sizer=wx.BoxSizer(wx.VERTICAL)
        hbox=wx.BoxSizer()
        for i in range(SPREAD_MAXIMUM_SPREAD_ROOMS):
            # initialize
            self.btnRoomLst.append([])
            self.lblFilterLst.append([])

            # 静态文本框(转发栏位)
            sbox=wx.StaticBox(panel, -1, f"Slot {i+1}")
            sbox.SetName(str(i+1))
            self.boxLst.append(sbox)
            sbs=wx.StaticBoxSizer(sbox,wx.VERTICAL)
            # 转发目的房间
            lblTo=wx.StaticText(panel,-1,"转发到房间:")
            lblTo.SetForegroundColour("grey")
            sbs.Add(lblTo)
            btnTo=wx.Button(panel,-1,size=(90,27))
            btnTo.SetName(f"{i};0")
            btnTo.Bind(wx.EVT_BUTTON,self.ShowSpRoomSelector)
            btnTo.Bind(wx.EVT_RIGHT_DOWN,self.UnSelectRoom)
            self.btnRoomLst[i].append(btnTo)
            sbs.Add(btnTo)
            # 转发来源房间 及 房间前缀过滤标识
            lblFrom=wx.StaticText(panel,-1,"监听下列房间:")
            lblFrom.SetForegroundColour("grey")
            sbs.Add(lblFrom)
            for j in range(1, SPREAD_MAXIMUM_LISTEN_ROOMS+1):
                btnFrom=wx.Button(panel,-1,size=(90,27))
                btnFrom.SetName(f"{i};{j}")
                btnFrom.Bind(wx.EVT_BUTTON,self.ShowSpRoomSelector)
                btnFrom.Bind(wx.EVT_RIGHT_DOWN,self.UnSelectRoom)
                self.btnRoomLst[i].append(btnFrom)
                hbox3=wx.BoxSizer()
                hbox3.Add(btnFrom,0,wx.RESERVE_SPACE_EVEN_IF_HIDDEN)
                lblFilter=wx.StaticText(panel,-1,"⚙",size=(25,25))
                lblFilter.SetName(f"{i};{j-1}")
                lblFilter.SetForegroundColour("grey")
                lblFilter.Bind(wx.EVT_LEFT_DOWN,self.ShowSpreadFilter)
                self.lblFilterLst[i].append(lblFilter)
                hbox3.Add(lblFilter,0,wx.LEFT|wx.TOP|wx.RESERVE_SPACE_EVEN_IF_HIDDEN,5)
                sbs.Add(hbox3,0,wx.RESERVE_SPACE_EVEN_IF_HIDDEN)
            # 开始/暂停按钮
            btnCtrl=wx.Button(panel,-1,size=(90,35))
            btnCtrl.SetName(str(i))
            btnCtrl.Bind(wx.EVT_BUTTON,self.ToggleSpreading)
            self.btnCtrlLst.append(btnCtrl)
            sbs.Add(btnCtrl,0,wx.UP|wx.RESERVE_SPACE_EVEN_IF_HIDDEN,10)
            hbox.Add(sbs,0,wx.ALL|wx.EXPAND,2)
        # 操作提示/转发成功数/转发失败数/待发送弹幕数/最近转发弹幕
        hbox2=wx.BoxSizer()
        lblHint=wx.StaticText(panel,-1,"左键选择房间，右键清除房间，⚙转发配置")
        lblHint.SetForegroundColour("grey")
        hbox2.Add(lblHint,0,wx.LEFT,5)
        self.lblSucc=wx.StaticText(panel,-1,"已转:0")
        self.lblSucc.SetForegroundColour("grey")
        hbox2.Add(self.lblSucc,0,wx.LEFT,12)
        self.lblFail=wx.StaticText(panel,-1,"失败:0")
        self.lblFail.SetForegroundColour("grey")
        hbox2.Add(self.lblFail,0,wx.LEFT,12)
        self.lblWait=wx.StaticText(panel,-1,"待发:0")
        self.lblWait.SetForegroundColour("grey")
        hbox2.Add(self.lblWait,0,wx.LEFT,12)
        self.lblRecent=wx.StaticText(panel,-1,"")
        self.lblRecent.SetForegroundColour("dark grey")
        self.sizer.Add(hbox2)
        self.sizer.Add(self.lblRecent)
        self.sizer.Add(hbox)
        panel.SetSizer(self.sizer)
        self.Bind(wx.EVT_CLOSE,self.OnClose)
        self.RefreshUI()
        # sync size
        panelBestSize=panel.GetBestSize()
        panelBestSize.SetWidth(panelBestSize.GetWidth()+15)
        panelBestSize.SetHeight(panelBestSize.GetHeight()+39) # FIXME: no clue about why StaticBoxSizer doesn't count start button's size. manually add magic 39 height for it.
        self.SetSize(panelBestSize)
    
    def ShowSpRoomSelector(self,event):
        btnRoom=event.GetEventObject()
        slot,index=btnRoom.GetName().split(";")
        if self.roomSelector:
            self.roomSelector.Destroy()
        self.roomSelector=SpRoomSelectFrame(self,int(slot),int(index))

    def ShowSpreadFilter(self,event):
        lblFilter=event.GetEventObject()
        slot,index=lblFilter.GetName().split(";")
        if self.spreadFilter:
            self.spreadFilter.Destory()
        self.spreadFilter=SpreadFilterFrame(self,int(slot),int(index))
    
    def SelectRoom(self,slot,index,roomid):
        old_rid=None
        if index<len(self.configs[slot][0]):
            old_rid=self.configs[slot][0][index]
            self.configs[slot][0][index]=roomid
            if index>0 and old_rid!=roomid:
                self.configs[slot][2][index-1]=""
                self.configs[slot][3][index-1]=0
        else:
            self.configs[slot][0].append(roomid)
            self.configs[slot][2].append("")
            self.configs[slot][3].append(0)
        if index>0 and self.configs[slot][1]:
            if roomid not in self.websockets.keys():
                self.websockets[roomid]=BiliLiveWebSocket(roomid)
            self.websockets[roomid].ChangeRefCount(+1)
            if old_rid is not None:
                self.websockets[old_rid].ChangeRefCount(-1)
        self.RefreshUI()
    
    def EditByRoomid(self,old,new):
        count=0
        for cfg in self.configs:
            for index,roomid in enumerate(cfg[0]):
                if roomid!=old: continue
                cfg[0][index]=new
                if index>0 and cfg[1]: count+=1
        if new not in self.websockets.keys():
            self.websockets[new]=BiliLiveWebSocket(new)
        self.websockets[new].ChangeRefCount(+count)
        if old in self.websockets.keys():
            self.websockets[old].ChangeRefCount(-count)
    
    def UnSelectByRoomid(self,roomid):
        count=0
        for cfg in self.configs:
            for index,rid in enumerate(cfg[0]):
                if roomid!=rid:
                    continue
                if index==0:
                    cfg[0][0]=None
                else:
                    cfg[0].pop(index)
                    cfg[2].pop(index-1)
                    cfg[3].pop(index-1)
                if index>0 and cfg[1]:
                    count+=1
            if cfg[0][0] is None and len(cfg[0])==1:
                cfg[1]=False
        if roomid in self.websockets.keys():
            self.websockets[roomid].ChangeRefCount(-count)
        self.RefreshUI()

    def UnSelectRoom(self,event):
        btnRoom=event.GetEventObject()
        if btnRoom.GetLabel()=="✚": return
        if self.roomSelector:
            self.roomSelector.Destroy()
        slot,index=btnRoom.GetName().split(";")
        slot,index=int(slot),int(index)
        if index==0:
            self.configs[slot][0][0]=None
        else:
            roomid=self.configs[slot][0].pop(index)
            self.configs[slot][2].pop(index-1)
            self.configs[slot][3].pop(index-1)
            if self.configs[slot][1]:
                self.websockets[roomid].ChangeRefCount(-1)
        if self.configs[slot][0][0] is None and len(self.configs[slot][0])==1:
            self.configs[slot][1]=False
        self.RefreshUI()
            
    def ToggleSpreading(self,event_or_int):
        if isinstance(event_or_int,int): slot=event_or_int
        else: slot=int(event_or_int.GetEventObject().GetName())
        self.configs[slot][1]=spreading=not self.configs[slot][1]
        for roomid in self.configs[slot][0][1:]:
            if roomid not in self.websockets.keys():
                self.websockets[roomid]=BiliLiveWebSocket(roomid)
            self.websockets[roomid].ChangeRefCount(+1 if spreading else -1)
        self.RefreshUI()
    
    def StopAll(self):
        any_spreading=False
        for slot,cfg in enumerate(self.configs):
            if cfg[1]:
                any_spreading=True
                self.ToggleSpreading(slot)
        return any_spreading
    
    def RefreshUI(self):
        for slot,cfg in enumerate(self.configs):
            idx=0
            for rid in cfg[0]:
                if rid is None:
                    self.btnRoomLst[slot][idx].SetLabel("✚")
                    self.btnRoomLst[slot][idx].SetForegroundColour("grey")
                    self.btnRoomLst[slot][idx].Show(True)
                else:
                    self.btnRoomLst[slot][idx].SetLabel(self.sp_rooms[rid][0])
                    self.btnRoomLst[slot][idx].SetForegroundColour("black")
                    self.btnRoomLst[slot][idx].Show(True)
                idx+=1
            self.boxLst[slot].SetLabel(f"Slot {slot+1}"+(" >>>"if cfg[1] else ""))
            self.boxLst[slot].SetForegroundColour("blue" if cfg[1] else "black")
            self.btnCtrlLst[slot].SetLabel("暂停转发" if cfg[1] else "开始转发")
            self.btnCtrlLst[slot].Show(bool(cfg[0][0]) or idx>1)
            if idx < SPREAD_MAXIMUM_LISTEN_ROOMS+1:
                self.btnRoomLst[slot][idx].SetLabel("✚")
                self.btnRoomLst[slot][idx].SetForegroundColour("grey")
                self.btnRoomLst[slot][idx].Show(bool(cfg[0][0]) or idx>1)
            for i in range(idx+1,SPREAD_MAXIMUM_LISTEN_ROOMS+1):
                self.btnRoomLst[slot][i].Show(False)
            idx=0
            for speaker_filters,spread_delays in zip(cfg[2],cfg[3]):
                room_setting_color="grey" if speaker_filters=="" and spread_delays==0 else "gold"
                self.lblFilterLst[slot][idx].SetForegroundColour(room_setting_color)
                self.lblFilterLst[slot][idx].Show(True)
                idx+=1
            for i in range(idx,SPREAD_MAXIMUM_LISTEN_ROOMS):
                self.lblFilterLst[slot][i].Show(False)
        self.Parent.SetSpreadButtonState(roomid=None,count=0,spreading=self.IsSpreading())
        self.Refresh()
        if self.spreadFilter:
            self.spreadFilter.Destroy()

    def OnClose(self,event):
        self.Show(False)
    
    def IsSpreading(self):
        return any([cfg[1] for cfg in self.configs])
    
    def RecordSucc(self,label):
        self.succ_count+=1
        UIChange(self.lblSucc,label=f"已转:{self.succ_count}")
        UIChange(self.lblRecent,label=label)
    
    def RecordFail(self):
        self.fail_count+=1
        UIChange(self.lblFail,label=f"失败:{self.fail_count}")

class SpreadFilterFrame(wx.Frame):
    def __init__(self, parent, slot, index):
        self.configs=parent.configs
        self.slot=slot
        self.index=index
        pos=parent.GetPosition()
        x,y=pos[0]+50,pos[1]+60
        wx.Frame.__init__(self, parent, title="房间转发设置", pos=(x,y), size=(300, 170),
        style=wx.DEFAULT_FRAME_STYLE ^ (wx.RESIZE_BORDER | wx.MAXIMIZE_BOX | wx.MINIMIZE_BOX) |wx.FRAME_FLOAT_ON_PARENT)
        if parent.show_pin:
            self.ToggleWindowStyle(wx.STAY_ON_TOP)
        panel=wx.Panel(self,-1,pos=(0,0),size=(300,90))
        wx.StaticText(panel,-1,"转发延迟",pos=(10,10))
        delay_value=int(self.configs[slot][3][index]*0.01)
        self.lblDelay=wx.StaticText(panel,-1,"",pos=(250,10))
        self.sldDelay=wx.Slider(panel,-1,pos=(60,6),size=(185,30),value=delay_value,minValue=0,maxValue=80)
        self.sldDelay.Bind(wx.EVT_SLIDER,self.OnDelayChange)
        self.OnDelayChange(None)
        wx.StaticText(panel,-1,"限定前缀",pos=(10,42))
        wx.StaticText(panel,-1,"仅转发指定的前缀，留空则不进行限制\n如果想指定多个前缀，请使用分号或逗号进行分隔",pos=(10,65)).SetForegroundColour("grey")
        speakers=self.configs[slot][2][index]
        self.tcFilter=wx.TextCtrl(panel,-1,speakers,pos=(68,38),size=(210,27),style=wx.TE_PROCESS_ENTER)
        self.tcFilter.Bind(wx.EVT_TEXT_ENTER,self.Save)
        self.btnSave=wx.Button(panel,-1,"保　存",pos=(105,105),size=(80,32))
        self.btnSave.Bind(wx.EVT_BUTTON,self.Save)
        self.Show()
    
    def OnDelayChange(self,event):
        delay_s=self.sldDelay.GetValue()*0.1
        self.lblDelay.SetLabel("%.1f s"%delay_s)
    
    def Save(self,event):
        speakers=self.tcFilter.GetValue().replace(" ","").replace("\u0592","")
        speakers=re.sub("[;；,，]+",";",speakers)
        speakers="" if speakers==";" else speakers
        self.configs[self.slot][2][self.index]=speakers
        self.configs[self.slot][3][self.index]=self.sldDelay.GetValue()*100
        self.Parent.RefreshUI() #该方法包含销毁本窗体的语句
