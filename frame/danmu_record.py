import wx,os,webbrowser,time
from utils.util import openFile, setFont,wxCopy,getTime,showInfoDialog

class DanmuRecordFrame(wx.Frame):
    def __init__(self,parent):
        SW,SH=wx.DisplaySize()
        wx.Frame.__init__(self, parent, title="弹幕发送记录", size=((SW//4,SH//4)), style=wx.DEFAULT_FRAME_STYLE)
        if parent.show_pin:
            self.ToggleWindowStyle(wx.STAY_ON_TOP)
        self.SetMinSize((SW//5,SH//8))
        self.SetMaxSize((SW//3,SH*4//5))
        self.Bind(wx.EVT_CLOSE,self.OnClose)
        self.rich=parent.enable_rich_record
        self.platform=parent.platform
        tc_style=wx.TE_MULTILINE|wx.TE_READONLY
        if self.rich:   tc_style|=wx.TE_RICH2
        self.tcRecord=wx.TextCtrl(self,style=tc_style)
        font_name="微软雅黑" if self.platform=="win" else None
        setFont(self.tcRecord,parent.record_fontsize,name=font_name)
        self.style:wx.TextAttr=self.tcRecord.GetDefaultStyle()
        menuBar = wx.MenuBar()
        menu = wx.Menu()
        menuBar.Append(menu,"　操作　")
        menu.Append(wx.ID_COPY,"复制全部","")
        menu.Append(wx.ID_CLEAR,"清空记录","")
        menu.Append(wx.ID_TOP,"置顶窗口","",wx.ITEM_CHECK)
        menu.Append(wx.ID_CLOSE,"关闭窗口\tEsc","")
        menu.Check(wx.ID_TOP,parent.show_pin)
        menu2 = wx.Menu()
        menuBar.Append(menu2,"　日志　")
        menu2.Append(wx.ID_FILE1,"本月屏蔽日志")
        menu2.Append(wx.ID_FILE2,"上月屏蔽日志")
        menu2.AppendSeparator()
        menu2.Append(wx.ID_FILE3,"当前房间近期弹幕日志")
        menu2.Append(wx.ID_FILE4,"日志文件目录")
        menu2.AppendSeparator()
        menu2.Append(wx.ID_NETWORK,"屏蔽词在线收集文档")
        self.SetMenuBar(menuBar)
        self.Bind(wx.EVT_MENU, self.MenuHandler)
        if parent.init_show_record:
            pos_x,pos_y=parent.Position[0]+parent.Size[0]+30,parent.Position[1]+30
            self.SetPosition((pos_x,pos_y))
            self.Show()

    def OnClose(self,event):
        self.Show(False)

    def MenuHandler(self,event):
        eventId=event.GetId()
        if eventId==wx.ID_CLOSE:
            self.OnClose(None)
        elif eventId==wx.ID_CLEAR:
            self.tcRecord.Clear()
        elif eventId==wx.ID_COPY:
            wxCopy(self.tcRecord.GetValue())
        elif eventId==wx.ID_TOP:
            self.ToggleWindowStyle(wx.STAY_ON_TOP)
        elif eventId==wx.ID_FILE1:
            path=os.getcwd()+"/logs/shielded/SHIELDED_%s.log"%getTime(fmt="%y-%m")
            try:    openFile(path,self.platform)
            except FileNotFoundError:   return showInfoDialog("本月暂未产生屏蔽记录","提示")
            except Exception as e:  return showInfoDialog("%s: %s"%(type(e),e),"打开日志失败")
            return True
        elif eventId==wx.ID_FILE2:
            ym=getTime(fmt="%y%m")
            y,m=int(ym[:2]),int(ym[2:])-1
            if m==0:    y,m=y-1,12
            path=os.getcwd()+"/logs/shielded/SHIELDED_%02d-%02d.log"%(y,m)
            try:    openFile(path,self.platform)
            except FileNotFoundError:   return showInfoDialog("上月未产生屏蔽记录","提示")
            except Exception as e:  return showInfoDialog("%s: %s"%(type(e),e),"打开日志失败")
            return True
        elif eventId==wx.ID_FILE3:
            roomid=self.Parent.roomid
            if not roomid:
                return showInfoDialog("未选择直播间","提示")
            if roomid not in self.Parent.danmu_log_dir.keys():
                return showInfoDialog("近期未在当前直播间发送过弹幕","提示")
            cur_time=int(time.time())
            dir_name=self.Parent.danmu_log_dir[roomid]
            for i in range(7):
                date=getTime(cur_time-86400*i,fmt="%y-%m-%d")
                path=os.getcwd()+"/logs/danmu/%s/%s.log"%(dir_name,date)
                try:    openFile(path,self.platform)
                except FileNotFoundError: continue
                except Exception as e:  return showInfoDialog("%s: %s"%(type(e),e),"打开日志失败")
                return True
            return showInfoDialog("近期未在当前直播间发送过弹幕","提示")
        elif eventId==wx.ID_FILE4:
            path=os.getcwd()+"/logs"
            try:    openFile(path,self.platform)
            except FileNotFoundError:   return showInfoDialog("日志目录不存在","打开日志目录失败")
            except Exception as e:  return showInfoDialog("%s: %s"%(type(e),e),"打开日志目录失败")
            return True
        elif eventId==wx.ID_NETWORK:
            webbrowser.open("https://docs.qq.com/sheet/DV2Nqb1NLd2hDeUt6")

    def AppendText(self,content,color="black"):
        if self.rich:
            self.style.SetTextColour(color)
            self.tcRecord.SetDefaultStyle(self.style)
        self.tcRecord.AppendText(content)

