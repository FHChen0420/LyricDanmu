import wx
import re

class SongMarkFrame(wx.Frame):
    def __init__(self, parent, src, song_id, tags, btn):
        self.parent=parent
        self.src=src
        self.song_id=song_id
        self.tags=tags
        self.relative_btn=btn
        icon=btn.GetLabel()
        if icon=="☆":
            self.ShowMarkFrame(parent, False)
        elif icon=="★":
            self.ShowMarkFrame(parent, True)

    def ShowMarkFrame(self, parent, marked):
        # 窗体
        pos=parent.GetPosition()
        title="收藏曲目 - "+("网易云" if self.src=="wy" else "QQ音乐")
        wx.Frame.__init__(self, parent, title=title, pos=(pos[0]+70,pos[1]+110), size=(375, 205),
                          style=wx.DEFAULT_FRAME_STYLE ^ (wx.RESIZE_BORDER | wx.MAXIMIZE_BOX) |wx.FRAME_FLOAT_ON_PARENT)
        if self.parent.show_pin:
            self.ToggleWindowStyle(wx.STAY_ON_TOP)
        p = wx.Panel(self, -1)
        txtId = wx.StaticText(p, -1, "ID", pos=(15, 15))
        tcId = wx.TextCtrl(p, -1, self.song_id, pos=(32, 11), size=(100, 27), style=wx.TE_READONLY)
        txtDesc = wx.StaticText(p, -1, "添加标签便于检索，使用分号或换行进行分割。", pos=(15, 45), size=(360,-1))
        self.tcTags = wx.TextCtrl(p, -1, self.tags, pos=(15, 67), size=(340, 100), style=wx.TE_MULTILINE)
        if marked:
            self.btnUnmark = wx.Button(p, -1, "取消收藏", pos=(180, 10), size=(80, 29))
            self.btnSave = wx.Button(p, -1, "保  存", pos=(275, 10), size=(80, 29))
            self.btnUnmark.Bind(wx.EVT_BUTTON,self.Unmark)
            self.btnSave.Bind(wx.EVT_BUTTON, self.Mark)
        else:
            self.btnMark = wx.Button(p, -1, "收  藏", pos=(275, 10), size=(80, 29))
            self.btnMark.Bind(wx.EVT_BUTTON, self.Mark)
        self.Show(True)

    def Mark(self,event):
        tags=self.tcTags.GetValue().strip()
        tags="*" if tags=="" else tags
        tags=re.sub(r"\r?\n|；",";",tags)
        tags=re.sub(r";+",";",tags)
        label=event.GetEventObject().GetLabel()
        self.parent.parent.Mark(self.src,self.song_id,tags)
        self.relative_btn.SetLabel("★")
        self.parent.txtMsg.SetForegroundColour("SEA GREEN")
        self.parent.txtMsg.SetLabel("已收藏歌曲" if label=="收  藏" else "已保存修改")
        self.Destroy()

    def Unmark(self,event):
        dlg = wx.MessageDialog(None, "确定要取消收藏吗？", "提示", wx.YES_NO|wx.NO_DEFAULT)
        if dlg.ShowModal()==wx.ID_YES:
            self.parent.parent.Unmark(self.src,self.song_id)
            self.relative_btn.SetLabel("☆")
            self.parent.txtMsg.SetForegroundColour("SEA GREEN")
            self.parent.txtMsg.SetLabel("已取消收藏")
            dlg.Destroy()
            self.Destroy()
        else:
            dlg.Destroy()

