import wx
from util import getRgbColor

class ColorFrame(wx.Frame):
    def __init__(self, parent):
        colors=parent.colors
        x=parent.Position[0]+10
        y=parent.Position[1]+parent.Size[1]-10
        W,H=8+25*len(colors),30
        if parent.platform=="win":
            style=wx.FRAME_FLOAT_ON_PARENT|wx.FRAME_TOOL_WINDOW
        else:
            style=wx.FRAME_FLOAT_ON_PARENT|wx.CAPTION
            y-=10
            H+=18
        wx.Frame.__init__(self, parent, title="",pos=(x,y),size=(W,H),style=style)
        self.panel=wx.Panel(self,-1,pos=(0,0),size=(W,H))
        self.panel.SetBackgroundColour("white")
        i=0
        for k,v in colors.items():
            btn=wx.Button(self.panel,-1,"██",pos=(5+25*i,4),size=(20,20),name=k)
            btn.SetForegroundColour(getRgbColor(k))
            btn.SetBackgroundColour(getRgbColor(k))
            btn.Bind(wx.EVT_BUTTON,self.ChangeColor)
            i+=1
        self.Show()
        self.Raise()
    
    def ChangeColor(self,event):
        color=event.GetEventObject().GetName()
        self.Parent.pool.submit(self.Parent.ThreadOfSetDanmuConfig,hex(int(color)),None)
        self.Parent.colorFrame=None
        self.Destroy()