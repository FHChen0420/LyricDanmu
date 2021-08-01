import wx
import time
import re
from pubsub import pub

def isEmpty(string):
    return string is None or string.strip()==""

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

def getTimeLineStr(t,style=0):
    m=t//60
    s=t-60*m
    fmt="%02d:%04.1f" if style==0 else "%2d:%02d"
    return fmt%(m,s)

def setWxUIAttr(obj,label=None,color=None,enabled=None):
    try:
        if color is not None: #注：颜色的设置最好在文本的设置之前进行
            obj.SetForegroundColour(color)
        if label is not None:
            obj.SetLabel(label)
        if enabled is not None:
            obj.Enable(enabled)
    except RuntimeError: pass
    except Exception as e:  raise e

def UIChange(obj,label=None,color=None,enabled=None):
    try: wx.CallAfter(pub.sendMessage,"ui_change",obj=obj,label=label,color=color,enabled=enabled)
    except Exception as e:  raise e

def setFont(obj,size,bold=False,name=None):
    weight=wx.FONTWEIGHT_BOLD if bold else wx.FONTWEIGHT_NORMAL
    try:
        if name is None:
            obj.SetFont(wx.Font(size,wx.FONTFAMILY_DEFAULT,wx.FONTSTYLE_NORMAL,weight))
        else:
            obj.SetFont(wx.Font(size,wx.FONTFAMILY_DEFAULT,wx.FONTSTYLE_NORMAL,weight,faceName=name))
    except RuntimeError: pass
    except Exception as e:  raise e

def getNodeValue(parent,childName):
    try:    return parent.getElementsByTagName(childName)[0].childNodes[0].nodeValue.strip()
    except IndexError:  return ""
    except Exception as e:  raise e

def splitTnL(line):
    fs,parts=[],line.split("]")
    if len(parts)<=1:   return []
    content = parts[-1].strip()
    for tl in parts[0:-1]:
        mo=re.match(r"\[(\d+):(\d+)(\.\d*)?",tl)
        if mo is None:  continue
        t_min,t_sec = int(mo.group(1)),int(mo.group(2))
        t_ms=0 if mo.group(3) is None else eval(mo.group(3))
        secnum = 60*t_min+t_sec+t_ms
        secfmt = "%2d:%02d"%(t_min,t_sec)
        secOrigin = mo.group()+"]"
        fs.append([secfmt, secnum, content, secOrigin]) #e.g. ["01:30", 90.233, "歌词内容", "[01:30.233]"]
    return fs

def showInfoDialog(content="",title=""):
    dlg = wx.MessageDialog(None, content, title, wx.OK)
    dlg.ShowModal()
    dlg.Destroy()
    return False