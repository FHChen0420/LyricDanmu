import re

import requests
import wx

from utils.api import BiliLiveAPI
from utils.util import showInfoDialog


class LiveroomSearchFrame(wx.Frame):
    MAX_RESULT=6
    def __init__(self, parent, keyword=""):
        self.blApi=BiliLiveAPI("")
        self.results=[]
        self.ShowFrame(parent)
        self.Search(keyword)
    
    def ShowFrame(self,parent):
        h=80+30*self.MAX_RESULT
        wx.Frame.__init__(self,parent,title="直播用户搜索结果",size=(260,h),
        style=wx.DEFAULT_FRAME_STYLE ^ (wx.RESIZE_BORDER | wx.MAXIMIZE_BOX | wx.MINIMIZE_BOX)|wx.FRAME_FLOAT_ON_PARENT)
        if parent.show_pin:
            self.ToggleWindowStyle(wx.STAY_ON_TOP)
        panel=wx.Panel(self,-1,pos=(0,0),size=(260,h))
        self.tcKeyword=wx.TextCtrl(panel,-1,"",pos=(20,10),size=(150,25),style=wx.TE_PROCESS_ENTER)
        self.tcKeyword.Bind(wx.EVT_TEXT_ENTER,self.OnSearch)
        btnSearch=wx.Button(panel,-1,"搜 索",pos=(180,10),size=(50,25))
        btnSearch.Bind(wx.EVT_BUTTON,self.OnSearch)
        self.btnResLst=[]
        for i in range(self.MAX_RESULT):
            btn=wx.Button(panel,-1,"",pos=(10,30*i+45),size=(240,27))
            btn.Bind(wx.EVT_BUTTON,self.OnRoomClick)
            btn.Show(False)
            self.btnResLst.append(btn)
    
    def Search(self,keyword):
        self.tcKeyword.SetValue(keyword)
        if keyword=="": return self.Show()
        try:
            data=self.blApi.search_live_users(keyword,self.MAX_RESULT)
            users=data["data"]["result"]
            self.results=[]
            for user in users:
                uname=re.sub('<em class="keyword">|</em>',"",user["uname"])
                self.results.append([user["roomid"],uname,user["attentions"]])
            self.results.sort(key=lambda x:-x[2])
        except requests.exceptions.ConnectionError:
            return showInfoDialog("网络异常，请重试", "搜索直播间出错")
        except requests.exceptions.ReadTimeout:
            return showInfoDialog("获取超时，请重试", "搜索直播间出错")
        except Exception:
            return showInfoDialog("解析错误，请重试", "搜索直播间出错")
        self.RefreshUI()
    
    def RefreshUI(self):
        result_num=len(self.results)
        for i,btn in enumerate(self.btnResLst):
            if i<result_num:
                user=self.results[i]
                fan_num=str(user[2]) if user[2]<10000 else "%.1f万"%(user[2]/10000)
                btn.SetLabel(f"{user[1]}　　{fan_num}关注")
                btn.SetName(f"{user[0]};{user[1]}")
                btn.Show(True)
            else:
                btn.Show(False)
        self.Show()
    
    def OnSearch(self,event):
        keyword=self.tcKeyword.GetValue().strip()
        self.Search(keyword)
    
    def OnRoomClick(self,event):
        obj=event.GetEventObject()
        roomid,rname=obj.GetName().split(";",1)
        rname=re.sub(r"(?i)[_\-]*(official|channel)","",rname)
        self.Parent.RecvSearchResult(roomid,rname)
        self.Destroy()
