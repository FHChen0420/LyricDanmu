import sys
import wx
import wx.lib.inspection

from frame.main import MainFrame


if __name__ == '__main__':
    app = wx.App()
    frame = MainFrame()
    if '--debug' in sys.argv:
        wx.lib.inspection.InspectionTool().Show()
    app.MainLoop()
