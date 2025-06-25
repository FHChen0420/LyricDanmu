import re

import wx

from utils.util import bindHint, showInfoDialog


class ShieldConfigFrame(wx.Frame):
    def __init__(self,parent):
        self.parent=parent
        wx.Frame.__init__(self, parent, title="屏蔽词管理", size=(290,330), style=wx.DEFAULT_FRAME_STYLE^ (wx.RESIZE_BORDER|wx.MAXIMIZE_BOX|wx.MINIMIZE_BOX))
        if parent.show_pin:
            self.ToggleWindowStyle(wx.STAY_ON_TOP)
        self.Bind(wx.EVT_CLOSE,self.OnClose)
        panel=wx.Panel(self,-1,pos=(0,0), size=(290,330))
        self.list = wx.ListCtrl(panel, -1, pos=(10,10), size=(260, 160),style = wx.LC_REPORT|wx.LC_SINGLE_SEL)
        self.list.InsertColumn(0, "")
        self.list.InsertColumn(1, "处理前")
        self.list.InsertColumn(2, "处理后")
        self.list.InsertColumn(3, "房间号")
        self.list.SetColumnWidth(0, 0)
        self.list.SetColumnWidth(1, 80)
        self.list.SetColumnWidth(2, 80)
        self.list.SetColumnWidth(3, 80)
        index=0
        for k,v in parent.custom_shields.items():
            self.list.InsertItem(index, "")
            self.list.SetItem(index,1,k)
            self.list.SetItem(index,2,v[1].replace("\\\\","\\"))
            self.list.SetItem(index,3,v[2] if v[2]!="" else "(ALL)")
            index+=1
        self.btnEdit=wx.Button(panel,-1,"修  改",pos=(10,175),size=(60,24))
        self.btnDelete=wx.Button(panel,-1,"删  除",pos=(80,175),size=(60,24))
        self.btnUpdateGlobal=wx.Button(panel,-1,"-获取最新词库-",pos=(160,175),size=(110,24))
        wx.StaticText(panel,-1,"处理前",pos=(10,207))
        self.tcBefore=wx.TextCtrl(panel,-1,"",pos=(55,205),size=(130,24))
        wx.StaticText(panel,-1,"处理后",pos=(10,237))
        self.tcAfter=wx.TextCtrl(panel,-1,"",pos=(55,235),size=(130,24))
        self.cbbDeal=wx.ComboBox(panel,-1,pos=(190,235),size=(80,24),style=wx.CB_READONLY,choices=["字符填充","内容替换"],value="字符填充")
        wx.StaticText(panel,-1,"房间号",pos=(10,267))
        self.tcRoom=wx.TextCtrl(panel,-1,"",pos=(55,265),size=(130,24))
        self.btnInsert=wx.Button(panel,-1,"添  加",pos=(190,265),size=(80,24))
        bindHint(wx.StaticText(panel,-1,"[?]",pos=(248,207)),
            "自定义屏蔽词规则详见说明文件\n \n"
            "屏蔽词对应的房间号为空时视为对所有房间生效\n"
            "有多个房间号时请使用逗号或分号隔开\n \n"
            "点击[获取最新词库]将会同步云端的屏蔽词库至本地\n"
            "云端屏蔽词库与用户自定义的屏蔽词无关"
        )
        self.btnDelete.Disable()
        self.btnEdit.Disable()
        self.tcAfter.Disable()
        self.list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnItemSelected)
        self.list.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.OnItemDeselected)
        self.cbbDeal.Bind(wx.EVT_COMBOBOX,self.OnDealChanged)
        self.tcBefore.Bind(wx.EVT_TEXT,self.OnTextChanged)
        self.btnInsert.Bind(wx.EVT_BUTTON,self.InsertItem)
        self.btnEdit.Bind(wx.EVT_BUTTON,self.EditItem)
        self.btnDelete.Bind(wx.EVT_BUTTON,self.DeleteItem)
        self.btnUpdateGlobal.Bind(wx.EVT_BUTTON,self.UpdateGlobalShield)

    def InsertItem(self,event):
        parent=self.parent
        shield_type=self.cbbDeal.GetSelection()
        before=self.tcBefore.GetValue().replace(" ","")
        after=self.tcAfter.GetValue().replace(" ","").replace("·","`")
        rooms=self.tcRoom.GetValue().replace(" ","")
        rooms=re.sub("[,，;；]",",",rooms)
        if len(before)==0:
            return showInfoDialog("屏蔽词不能为空", "添加屏蔽规则出错")
        if before==after:
            return showInfoDialog("屏蔽前后无变化", "添加屏蔽规则出错")
        if not re.match(r"^[\d,]*$",rooms):
            return showInfoDialog("房间号格式有误", "添加屏蔽规则出错")
        index=0
        for k in self.parent.custom_shields.keys():
            if before==k:
                dlg = wx.MessageDialog(None, "屏蔽词已在列表中，是否更新处理规则？", "提示", wx.YES_NO|wx.YES_DEFAULT)
                update = dlg.ShowModal()==wx.ID_YES
                dlg.Destroy()
                if update: break
                else: return
            index+=1
        if index>=self.list.GetItemCount():
            self.list.InsertItem(index, "")
        self.list.SetItem(index,1,before)
        self.list.SetItem(index,2,after)
        self.list.SetItem(index,3,rooms if rooms!="" else "(ALL)")
        self.list.Select(index)
        parent.custom_shields[before]=[shield_type,after.replace("\\","\\\\"),rooms]
        self.UpdateRoomShield(rooms)
        self.tcBefore.Clear()
        self.tcAfter.Clear()
        self.tcRoom.Clear()
    
    def EditItem(self,event):
        index=self.list.GetFirstSelected()
        if index==-1:   return
        before=self.list.GetItem(index,1).GetText()
        after=self.list.GetItem(index,2).GetText()
        rooms=self.list.GetItem(index,3).GetText()
        deal_type=self.parent.custom_shields[before][0]
        self.tcBefore.SetValue(before)
        self.cbbDeal.SetSelection(deal_type)
        self.tcAfter.SetValue(after)
        self.tcAfter.Enable(deal_type==1)
        self.tcRoom.SetValue("" if rooms=="(ALL)" else rooms)
    
    def DeleteItem(self,event):
        parent=self.parent
        index=self.list.GetFirstSelected()
        if index==-1:   return
        before=self.list.GetItem(index,1).GetText()
        rooms=self.list.GetItem(index,3).GetText()
        self.list.DeleteItem(index)
        parent.custom_shields.pop(before)
        self.UpdateRoomShield("" if rooms=="(ALL)" else rooms)

    def OnItemSelected(self,event):
        self.btnEdit.Enable()
        self.btnDelete.Enable()
    
    def OnItemDeselected(self,event):
        self.btnEdit.Disable()
        self.btnDelete.Disable()

    def OnTextChanged(self,event):
        if self.cbbDeal.GetSelection()==1:  return
        before=self.tcBefore.GetValue().replace(" ","")
        so=re.search(r"#[1-9]",before)
        if so is not None:
            after=re.sub(r"#([1-9])",lambda x:"`"*int(x.group(1)),before,count=1)
            after=re.sub(r"#[1-9]","",after)
        else:
            after=before[0]+"`"+before[1:] if len(before)>=2 else before
        self.tcAfter.SetValue(after)

    def OnDealChanged(self,event):
        self.tcAfter.Enable(self.cbbDeal.GetSelection()==1)
        self.OnTextChanged(None)
    
    def OnClose(self,event):
        self.Show(False)

    def UpdateGlobalShield(self,event):
        self.parent.pool.submit(self.parent.ThreadOfUpdateGlobalShields)
    
    def UpdateRoomShield(self,roomids):
        room_anti_shields:dict=self.parent.room_anti_shields
        room_keys = room_anti_shields.keys()
        if roomids=="":
            for roomid in room_keys:
                self.parent.GetRoomShields(roomid,update=True)
        else:
            for roomid in roomids.split(","):
                if roomid in room_keys:
                    self.parent.GetRoomShields(roomid,update=True)
