import wx
import wx.html2

class LivePlayerFrame(wx.Frame):
    def __init__(self, parent):
        wx.Frame.__init__(self, parent, -1, "LivePlayer", size=(960,540),style=wx.DEFAULT_FRAME_STYLE)
        backend=wx.html2.WebViewBackendEdge if parent.platform=="win" else wx.html2.WebViewBackendWebKit
        self.browser = wx.html2.WebView.New(self,backend=backend)
        self.browser.LoadURL("http://127.0.0.1:8080/player.html")
        self.Show()
        