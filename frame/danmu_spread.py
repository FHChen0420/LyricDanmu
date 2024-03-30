import re
import time

import wx
from pubsub import pub

from const.constant import ERR_INFO, InternalMessage, SpreadEventTypes
from frame.spread_room_select import SpRoomSelectFrame
from utils.live_websocket import BiliLiveWebSocket
from utils.util import UIChange, getTime, setFont
from utils.controls import AutoPanel

UI_ROOT_MARGIN = (0, 8, 8, 8) # Top | Right | Bottom | Left
UI_ROOT_SPACING = 4

class DanmuSpreadFrame(wx.Frame):
    def __init__(self, parent):
        # 消息订阅
        pub.subscribe(self.OnMessageCoreConfigUpdated, InternalMessage.CORE_CONFIG_UPDATED.value) # 消息：应用设置保存时
        pub.subscribe(self.OnMessageSpreadEvent, InternalMessage.SPREAD_EVENT.value)              # 消息：应用设置发生变化

        # 基础配置
        self.configs=parent.sp_configs # 每项为[房间号列表,转发开关,限定前缀列表,转发延时列表]
        self.sp_rooms=parent.sp_rooms
        self.websockets=parent.ws_dict
        self.show_pin=parent.show_pin
        self.roomSelector=None
        self.spreadFilter=None
        self.succ_count=0
        self.fail_count=0
        self.btnRoomLst=[]
        self.lblFilterLst=[]
        self.btnCtrlLst=[]
        self.boxLst=[]
        self.logViewerVerboseMode = False
        self.maximumSpreadRooms = parent.spread_maximum_spread_rooms
        self.maximumListenRooms = parent.spread_maximum_listen_rooms

        # 初始化窗体
        super().__init__(
            parent,
            title = "弹幕转发配置",
            style = wx.DEFAULT_FRAME_STYLE ^ (wx.RESIZE_BORDER | wx.MAXIMIZE_BOX | wx.MINIMIZE_BOX),
        )
        if parent.show_pin:
            self.ToggleWindowStyle(wx.STAY_ON_TOP)
        self.SetBackgroundColour(wx.NullColour)

        # 根节点
        verticalBoxSizer = wx.BoxSizer(wx.VERTICAL)
        horizontalBoxSizer = wx.BoxSizer()
        self.sizer = verticalBoxSizer
        self.SetSizer(verticalBoxSizer)
        panel = AutoPanel(self, wx.VERTICAL, UI_ROOT_SPACING)
        verticalBoxSizer.AddSpacer(UI_ROOT_MARGIN[0])
        verticalBoxSizer.Add(horizontalBoxSizer)
        verticalBoxSizer.AddSpacer(UI_ROOT_MARGIN[2])
        horizontalBoxSizer.AddSpacer(UI_ROOT_MARGIN[3])
        horizontalBoxSizer.Add(panel)
        horizontalBoxSizer.AddSpacer(UI_ROOT_MARGIN[1])

        # 提示信息
        infoRow = panel.AddToSizer(AutoPanel(panel, spacing = 12), flag = wx.EXPAND)
        infoRow.AddToSizer(wx.StaticText(infoRow,-1,"左键选择房间，右键清除房间，⚙转发配置")).SetForegroundColour("grey")
        self.lblSucc = infoRow.AddToSizer(wx.StaticText(infoRow,-1,"已转:0"))
        self.lblSucc.SetForegroundColour("grey")
        self.lblFail = infoRow.AddToSizer(wx.StaticText(infoRow,-1,"失败:0"))
        self.lblFail.SetForegroundColour("grey")
        self.lblWait = infoRow.AddToSizer(wx.StaticText(infoRow,-1,"待发:0"))
        self.lblWait.SetForegroundColour("grey")

        # 最近历史
        self.lblRecent = panel.AddToSizer(wx.StaticText(panel,-1,""))
        self.lblRecent.SetForegroundColour("dark grey")

        # 房间配置
        configRow = panel.AddToSizer(AutoPanel(panel, wx.HORIZONTAL, 4))
        for i in range(self.maximumSpreadRooms):
            self.btnRoomLst.append([])
            self.lblFilterLst.append([])

            box = wx.StaticBox(configRow, -1, f"Slot {i+1}")
            sizer = configRow.AddToSizer(wx.StaticBoxSizer(box, wx.VERTICAL), flag = wx.ALL, border = 2)
            self.boxLst.append(box)

            # 转发目的房间
            lblTo=wx.StaticText(box,-1,"转发到房间:")
            lblTo.SetForegroundColour("grey")
            sizer.Add(lblTo)

            btnTo=wx.Button(box,-1,size=(90,27))
            btnTo.SetName(f"{i};0")
            btnTo.Bind(wx.EVT_BUTTON,self.ShowSpRoomSelector)
            btnTo.Bind(wx.EVT_RIGHT_DOWN,self.UnSelectRoom)
            self.btnRoomLst[i].append(btnTo)
            sizer.Add(btnTo)

            # 转发来源房间 及 房间前缀过滤标识
            lblFrom=wx.StaticText(box,-1,"监听下列房间:")
            lblFrom.SetForegroundColour("grey")
            sizer.Add(lblFrom)
            for j in range(1, self.maximumListenRooms+1):
                row = AutoPanel(box, spacing = 6)
                sizer.Add(row, flag = wx.RESERVE_SPACE_EVEN_IF_HIDDEN)

                # 来源按钮
                btnFrom=row.AddToSizer(wx.Button(row,-1,size=(90,27)), flag = wx.RESERVE_SPACE_EVEN_IF_HIDDEN)
                btnFrom.SetName(f"{i};{j}")
                btnFrom.Bind(wx.EVT_BUTTON,self.ShowSpRoomSelector)
                btnFrom.Bind(wx.EVT_RIGHT_DOWN,self.UnSelectRoom)
                self.btnRoomLst[i].append(btnFrom)

                # 过滤按钮
                lblFilter=row.AddToSizer(wx.StaticText(row,-1,"⚙", size=(18, -1)), flag = wx.RESERVE_SPACE_EVEN_IF_HIDDEN | wx.ALIGN_CENTER)
                lblFilter.SetName(f"{i};{j-1}")
                lblFilter.SetForegroundColour("grey")
                lblFilter.Bind(wx.EVT_LEFT_DOWN,self.ShowSpreadFilter)
                self.lblFilterLst[i].append(lblFilter)
                row.GetSizer().AddSpacer(4)

            # 开始/暂停按钮
            btnCtrl=wx.Button(box,-1,size=(90,35))
            btnCtrl.SetName(str(i))
            btnCtrl.Bind(wx.EVT_BUTTON,self.ToggleSpreading)
            self.btnCtrlLst.append(btnCtrl)
            sizer.Add(btnCtrl,0,wx.UP|wx.RESERVE_SPACE_EVEN_IF_HIDDEN,10)

        # 转发日志
        self.tcLogViewer = panel.AddToSizer(wx.TextCtrl(panel, style = wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2, size=(-1, 240)), flag = wx.EXPAND)
        self.tcLogViewer.Show(False)
        setFont(self.tcLogViewer, 9, name="微软雅黑" if self.Parent.platform=="win" else None)

        self.Bind(wx.EVT_CLOSE,self.OnClose)
        self.SyncConfig()
        self.FitSizeForContent()
        self.RefreshUI()
    
    def FitSizeForContent(self):
        self.Fit()

    def SyncConfig(self):
        self.OnMessageCoreConfigUpdated(self.Parent.GenerateConfigSnapshot(schemeOnly = True), self.Parent.GenerateConfigSnapshot())
    
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
            self.spreadFilter.Destroy()
        self.spreadFilter=SpreadFilterFrame(self,int(slot),int(index))
    
    def SelectRoom(self,slot,index,roomid):
        old_rid=None
        if index<len(self.configs[slot][0]):
            old_rid=self.configs[slot][0][index]
            self.configs[slot][0][index]=roomid
            if index>0 and old_rid!=roomid:
                self.configs[slot][2][index-1]=""
                self.configs[slot][3][index-1]=0
                self.configs[slot][4][index-1]=False
        else:
            self.configs[slot][0].append(roomid)
            self.configs[slot][2].append("")
            self.configs[slot][3].append(0)
            self.configs[slot][4].append(False)
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
            self.configs[slot][4].pop(index-1)
            if self.configs[slot][1]:
                self.websockets[roomid].ChangeRefCount(-1)
        if self.configs[slot][0][0] is None and len(self.configs[slot][0])==1:
            self.configs[slot][1]=False
        self.RefreshUI()
            
    def ToggleSpreading(self,event_or_int):
        if isinstance(event_or_int,int): slot=event_or_int
        else: slot=int(event_or_int.GetEventObject().GetName())
        self.configs[slot][1]=spreading=not self.configs[slot][1]
        pub.sendMessage(InternalMessage.SPREAD_EVENT.value, eventType = SpreadEventTypes.START if spreading else SpreadEventTypes.STOP , eventData = {
            "internalTime": int(time.time()),
            "internalData": {
                "slot": slot,
            },
        })
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
            if idx < self.maximumListenRooms+1:
                self.btnRoomLst[slot][idx].SetLabel("✚")
                self.btnRoomLst[slot][idx].SetForegroundColour("grey")
                self.btnRoomLst[slot][idx].Show(bool(cfg[0][0]) or idx>1)
            for i in range(idx+1,self.maximumListenRooms+1):
                self.btnRoomLst[slot][i].Show(False)
            idx=0
            for speaker_filters,spread_delays in zip(cfg[2],cfg[3]):
                room_setting_color="grey" if speaker_filters=="" and spread_delays==0 else "gold"
                self.lblFilterLst[slot][idx].SetForegroundColour(room_setting_color)
                self.lblFilterLst[slot][idx].Show(True)
                idx+=1
            for i in range(idx,self.maximumListenRooms):
                self.lblFilterLst[slot][i].Show(False)
        self.Parent.SetSpreadButtonState(roomid=None,count=0,spreading=self.IsSpreading())
        self.Refresh()
        if self.spreadFilter:
            self.spreadFilter.Destroy()

    def AppendLogToLogViewer(self, content, color):
        style = self.tcLogViewer.GetDefaultStyle()
        style.SetTextColour(color)
        self.tcLogViewer.SetDefaultStyle(style)
        self.tcLogViewer.AppendText("{lineWrap}{content}".format(content = content, lineWrap = "\n" if len(self.tcLogViewer.GetValue()) > 0 else ""))

    def OnMessageCoreConfigUpdated(self, before, after):
        shouldResize = False

        if before["spread_logviewer_enabled"] != after["spread_logviewer_enabled"]:
            self.tcLogViewer.Show(after["spread_logviewer_enabled"])
            shouldResize = True

        self.logViewerVerboseMode = after["spread_logviewer_verbose"]

        if before["spread_logviewer_height"] != after["spread_logviewer_height"]:
            self.tcLogViewer.SetMinSize((-1, after["spread_logviewer_height"]))
            shouldResize = True

        if shouldResize:
            self.FitSizeForContent()

    def OnMessageSpreadEvent(self, eventType: SpreadEventTypes, eventData):
        internalTimeText = getTime(eventData["internalTime"])
        internalData = eventData["internalData"]
        slot = internalData["slot"]
        if slot != None:
            slot = slot + 1

        if eventType == SpreadEventTypes.START:
            self.AppendLogToLogViewer(
                "{internalTimeText} | #{slot} | 开始转发".format(**{
                    "internalTimeText": internalTimeText,
                    "slot": slot,
                }),
                "medium aquamarine",
            )
        elif eventType == SpreadEventTypes.STOP:
            self.AppendLogToLogViewer(
                "{internalTimeText} | #{slot} | 停止转发".format(**{
                    "internalTimeText": internalTimeText,
                    "slot": slot,
                }),
                "tan",
            )
        elif eventType == SpreadEventTypes.RECEIVE_VALID_TRANSLATED:
            if self.logViewerVerboseMode:
                self.AppendLogToLogViewer(
                    "{internalTimeText} | #{slot}.{fromRoomFull} | 捕获到：{rawContent}".format(**{
                        "internalTimeText": internalTimeText,
                        "slot": slot,
                        "fromRoomFull": internalData["fromRoom"]["full"],
                        "rawContent": internalData["rawContent"],
                    }),
                    "gray",
                )
        elif eventType == SpreadEventTypes.RECEIVE_INVALID_TRANSLATED:
            if self.logViewerVerboseMode:
                self.AppendLogToLogViewer(
                    "{internalTimeText} | #{slot}.{fromRoomFull} | 捕获到前缀不符：{rawContent}".format(**{
                        "internalTimeText": internalTimeText,
                        "slot": slot,
                        "fromRoomFull": internalData["fromRoom"]["full"],
                        "rawContent": internalData["rawContent"],
                    }),
                    "gray",
                )
        elif eventType == SpreadEventTypes.SENT:
            style = ERR_INFO[eventData["result"]]
            self.AppendLogToLogViewer(
                "{internalTimeText} | #{slot}.{fromRoomFull}->{toRoomFull} | {stylePrefix}{message}".format(**{
                    "internalTimeText": internalTimeText,
                    "slot": slot,
                    "fromRoomFull": internalData["fromRoom"]["full"],
                    "toRoomFull": internalData["toRoom"]["full"],
                    "stylePrefix": style[0],
                    "message": eventData["message"],
                }),
                style[1],
            )

    def Destroy(self):
        pub.unsubscribe(self.OnMessageCoreConfigUpdated, InternalMessage.CORE_CONFIG_UPDATED.value)
        pub.unsubscribe(self.OnMessageSpreadEvent, InternalMessage.SPREAD_EVENT.value)
        return super().Destroy()
        
    def OnClose(self,event):
        self.Show(False)
        if self.roomSelector:
            self.roomSelector.Destroy()
            self.roomSelector = None
        if self.spreadFilter:
            self.spreadFilter.Destroy()
            self.spreadFilter = None
    
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
        wx.Frame.__init__(self, parent, title="房间转发设置", pos=(x,y), size=(300, 235),
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
        speakers=self.configs[slot][2][index]
        self.tcFilter=wx.TextCtrl(panel,-1,speakers,pos=(68,38),size=(210,27),style=wx.TE_PROCESS_ENTER)
        self.tcFilter.Bind(wx.EVT_TEXT_ENTER,self.Save)
        wx.StaticText(panel,-1,"仅转发指定的前缀，留空则不进行限制\n"
                      "如果想指定多个前缀，请使用分号或逗号进行分隔\n"
                      "如果想转发无前缀的弹幕，请填入该房间的主播简称",
                      pos=(10,65)).SetForegroundColour("grey")
        wx.StaticText(panel,-1,"覆盖前缀",pos=(10,125))
        self.ckbOverride=wx.CheckBox(panel, -1, "使用主播简称覆盖原本前缀",pos=(68,125))
        self.ckbOverride.SetValue(self.configs[slot][4][index])
        self.btnSave=wx.Button(panel,-1,"保　存",pos=(105,160),size=(80,32))
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
        self.configs[self.slot][4][self.index]=self.ckbOverride.GetValue()
        self.Parent.RefreshUI() #该方法包含销毁本窗体的语句
