import wx
import wx.html2

class PlayerFrame(wx.Frame):
    def __init__(self, parent):
        if not wx.html2.WebView.IsBackendAvailable(wx.html2.WebViewBackendEdge):
            return wx.MessageBox("＊请检查电脑是否安装了Edge/Chrome浏览器\n"+
            "＊请检查工具目录下是否存在对应版本(x64或x86)的WebView2Loader.dll文件","自带窗口打开失败")
        wx.Frame.__init__(self, parent, -1, "LivePlayer", size=(1280,720),style=wx.DEFAULT_FRAME_STYLE)
        self.browser = wx.html2.WebView.New(self,backend=wx.html2.WebViewBackendEdge)
        self.browser.LoadURL("http://127.0.0.1:8080/player.html")
        self.Show()