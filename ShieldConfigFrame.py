import wx
import re

class ShieldConfigFrame(wx.Frame):
    def __init__(self,parent):
        self.parent=parent
        wx.Frame.__init__(self, parent, title="屏蔽词管理", size=(290,300), style=wx.DEFAULT_FRAME_STYLE^ (wx.RESIZE_BORDER|wx.MAXIMIZE_BOX|wx.MINIMIZE_BOX))
        if parent.show_pin:
            self.ToggleWindowStyle(wx.STAY_ON_TOP)
        self.Bind(wx.EVT_CLOSE,self.OnClose)
        panel=wx.Panel(self,-1,pos=(0,0), size=(290,300))
        self.list = wx.ListCtrl(panel, -1, pos=(10,10), size=(260, 160),style = wx.LC_REPORT|wx.LC_SINGLE_SEL)
        self.list.InsertColumn(0, "")
        self.list.InsertColumn(1, "处理前")
        self.list.InsertColumn(2, "处理后")
        self.list.SetColumnWidth(0, 0)
        self.list.SetColumnWidth(1, 120)
        self.list.SetColumnWidth(2, 120)
        index=0
        for k,v in parent.custom_shields.items():
            self.list.InsertItem(index, "")
            self.list.SetItem(index,1,k)
            self.list.SetItem(index,2,v[1])
            index+=1
        self.btnDelete=wx.Button(panel,-1,"删  除",pos=(10,175),size=(80,24))
        wx.StaticText(panel,-1,"屏蔽词库",pos=(135,178))
        self.btnUpdate=wx.Button(panel,-1,"-更新-",pos=(190,175),size=(80,24))
        self.btnInsert=wx.Button(panel,-1,"新  增",pos=(190,205),size=(80,24))
        wx.StaticText(panel,-1,"处理前",pos=(10,207))
        self.tcBefore=wx.TextCtrl(panel,-1,"",pos=(55,205),size=(130,24))
        wx.StaticText(panel,-1,"处理后",pos=(10,237))
        self.cbbDeal=wx.ComboBox(panel,-1,pos=(55,235),size=(80,24),style=wx.CB_READONLY,choices=["字符填充","内容替换"],value="字符填充")
        self.tcAfter=wx.TextCtrl(panel,-1,"",pos=(140,235),size=(130,24))
        self.btnDelete.Disable()
        self.tcAfter.Disable()
        self.list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnItemSelected)
        self.list.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.OnItemDeselected)
        self.cbbDeal.Bind(wx.EVT_COMBOBOX,self.OnDealChanged)
        self.tcBefore.Bind(wx.EVT_TEXT,self.OnTextChanged)
        self.btnInsert.Bind(wx.EVT_BUTTON,self.InsertItem)
        self.btnUpdate.Bind(wx.EVT_BUTTON,self.UpdateGlobalShield)
        self.btnDelete.Bind(wx.EVT_BUTTON,self.DeleteItem)

    def InsertItem(self,event):
        before=self.tcBefore.GetValue().replace(" ","")
        after=self.tcAfter.GetValue().replace(" ","")
        if len(before)==0:
            dlg = wx.MessageDialog(None, "屏蔽词不能为空", "添加屏蔽规则出错", wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
            return
        so=re.search(r"\\(?![1-9])|[\(\)\[\]\{\}\.\+\*\^\$\?\|]",before)
        if so is not None or self.cbbDeal.GetSelection()==1 and "\\" in before:
            dlg = wx.MessageDialog(None, "屏蔽词含特殊字符", "添加屏蔽规则出错", wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
            return
        if before==after:
            dlg = wx.MessageDialog(None, "屏蔽前后无变化", "添加屏蔽规则出错", wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
            return
        index=0
        for k,v in self.parent.custom_shields.items():
            if before==k:
                dlg = wx.MessageDialog(None, "屏蔽词已在列表中，是否更新处理规则？", "提示", wx.YES_NO|wx.YES_DEFAULT)
                if dlg.ShowModal()==wx.ID_YES:
                    dlg.Destroy()
                    break
                else:
                    dlg.Destroy()
                    return
            index+=1
        if index>=self.list.GetItemCount():
            self.list.InsertItem(index, "")
        self.list.SetItem(index,1,before)
        self.list.SetItem(index,2,after)
        self.list.Select(index)
        self.parent.custom_shields[before]=[self.cbbDeal.GetSelection(),after]
        self.parent.shield_changed = True
        self.tcBefore.Clear()
        self.tcAfter.Clear()
    
    def DeleteItem(self,event):
        index=self.list.GetFirstSelected()
        if index==-1:   return
        before=self.list.GetItem(index,1).GetText()
        self.list.DeleteItem(index)
        self.parent.custom_shields.pop(before)
        self.parent.shield_changed = True

    def OnItemSelected(self,event):
        self.btnDelete.Enable()
    
    def OnItemDeselected(self,event):
        self.btnDelete.Disable()

    def OnTextChanged(self,event):
        if self.cbbDeal.GetSelection()==1:  return
        before=self.tcBefore.GetValue().replace(" ","")
        so=re.search(r"\\(?![1-9])|[\(\)\[\]\{\}\.\+\*\^\$\?\|]",before)
        if so is not None:
            self.tcAfter.SetValue(" <错误> ")
            return
        so=re.search(r"\\[1-9]",before)
        if so is not None:
            after=re.sub(r"\\([1-9])",lambda x:"`"*int(x.group(1)),before,count=1)
            after=re.sub(r"\\[1-9]","",after)
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