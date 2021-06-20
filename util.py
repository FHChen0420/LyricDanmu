import wx
import time

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