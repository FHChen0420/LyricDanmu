import sys
import argparse
import wx
import wx.lib.inspection

from frame.main import MainFrame


if __name__ == '__main__':
    argParser = argparse.ArgumentParser()
    argParser.add_argument('--debug', help='enable debug mode', action='store_true', required=False)
    argParser.add_argument('--account', type=int, default=1, help='default account slot', required=False)

    args = argParser.parse_args(sys.argv[1:])

    app = wx.App()
    frame = MainFrame()
    if args.debug:
        wx.lib.inspection.InspectionTool().Show()
    if args.account:
        frame.SwitchAccount(args.account - 1)
    app.MainLoop()
