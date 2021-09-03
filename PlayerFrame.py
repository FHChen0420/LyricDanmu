import wx
import wx.html2

class PlayerFrame(wx.Frame):
    def __init__(self, parent):
        if parent.platform=="win" and not wx.html2.WebView.IsBackendAvailable(wx.html2.WebViewBackendEdge):
            return wx.MessageBox("＊请检查电脑是否安装了Edge/Chrome浏览器\n"+
            "＊如果电脑是32位系统，请将源码中的dll/x86/WebView2Loader.dll文件下载到工具目录下（dll和exe文件应位于同级目录）","自带窗口打开失败")
        wx.Frame.__init__(self, parent, -1, "LivePlayer", size=(960,540),style=wx.DEFAULT_FRAME_STYLE)
        backend=wx.html2.WebViewBackendEdge if parent.platform=="win" else wx.html2.WebViewBackendWebKit
        self.browser = wx.html2.WebView.New(self,backend=backend)
        self.browser.LoadURL("http://127.0.0.1:8080/player.html")
        self.Show()
        