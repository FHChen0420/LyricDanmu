import wx
import time
from pubsub import pub

def getRgbColor(num):
    num=int(num)
    r=num//65536
    g=(num-65536*r)//256
    b=num-65536*r-256*g
    return wx.Colour(r,g,b)

def getTime(ts=None,ms=False,fmt="%H:%M:%S"):
    if ts is None:  ts=time.time()
    elif ms:        ts=ts/1000
    return time.strftime(fmt,time.localtime(ts))

def getTimeLineStr(t):
    m=t//60
    s=t-60*m
    return "%02d:%04.1f"%(m,s)

def setWxUIAttr(obj,label=None,color=None,enabled=None):
    try:
        if color is not None: #注：颜色的设置最好在文本的设置之前进行
            obj.SetForegroundColour(color)
        if label is not None:
            obj.SetLabel(label)
        if enabled is not None:
            obj.Enable(enabled)
    except RuntimeError:
        pass

def UIChange(obj,label=None,color=None,enabled=None):
    wx.CallAfter(pub.sendMessage,"attr",obj=obj,label=label,color=color,enabled=enabled)
    