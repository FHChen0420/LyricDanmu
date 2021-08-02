import re, time, wx
from typing import Optional
from pubsub import pub
from constant import REGEX_CHAR_TRANSFORM_RULES

def isEmpty(string) -> bool:
    """判断字符串是否为空"""
    return string is None or string.strip()==""

def getRgbColor(num:int) -> wx.Colour:
    """根据整数生成对应的wxUI颜色"""
    num=int(num)
    r=num//65536
    g=(num-65536*r)//256
    b=num-65536*r-256*g
    return wx.Colour(r,g,b)

def getTime(ts=None,ms=False,fmt="%H:%M:%S") -> str:
    """将时间戳ts按fmt格式进行转化，ms表示ts是否为毫秒级时间戳"""
    if ts is None:  ts=time.time()
    elif ms:        ts=ts/1000
    return time.strftime(fmt,time.localtime(ts))

def getTimeLineStr(seconds,style=0) -> str:
    """将秒数转化为时钟格式
    
    : style=0 -> MM:SS.X　　style!=0 -> MM:SS"""
    min=seconds//60
    sec=seconds-60*min
    fmt="%02d:%04.1f" if style==0 else "%2d:%02d"
    return fmt%(min,sec)

def setWxUIAttr(obj:wx.Control,label=None,color:Optional[wx.Colour]=None,enabled=None):
    """设置wxUI部件的显示文本、前景色、是否启用"""
    try:
        if color is not None:   obj.SetForegroundColour(color)
        if label is not None:   obj.SetLabel(label)
        if enabled is not None: obj.Enable(enabled)
    except RuntimeError: pass
    except Exception as e:  raise e

def UIChange(obj:wx.Control,label=None,color:Optional[wx.Colour]=None,enabled=None):
    """主线程调用函数来设置wxUI部件的显示文本、前景色、是否启用"""
    try: wx.CallAfter(pub.sendMessage,"ui_change",obj=obj,label=label,color=color,enabled=enabled)
    except Exception as e:  raise e

def setFont(obj:wx.Control,size,bold=False,name=None):
    """设置wxUI部件的字体大小、是否加粗、字体名称"""
    weight=wx.FONTWEIGHT_BOLD if bold else wx.FONTWEIGHT_NORMAL
    try:
        if name is None:
            obj.SetFont(wx.Font(size,wx.FONTFAMILY_DEFAULT,wx.FONTSTYLE_NORMAL,weight))
        else:
            obj.SetFont(wx.Font(size,wx.FONTFAMILY_DEFAULT,wx.FONTSTYLE_NORMAL,weight,faceName=name))
    except RuntimeError: pass
    except Exception as e:  raise e

def getNodeValue(parentNode,childName) -> str:
    """获取DOM父节点parentNode下名为childName的子节点的值"""
    try:    return parentNode.getElementsByTagName(childName)[0].childNodes[0].nodeValue.strip()
    except IndexError:  return ""
    except Exception as e:  raise e

def splitTnL(lrc_line:str) -> list:
    """对lrc格式的歌词行进行处理，分离时间轴与歌词内容

    :示例输入："[01:35.49]壊れていたのは世界ではなくて"
    :示例输出：[["01:35", 95.49, "壊れていたのは世界ではなくて", "[01:35.49]"]]
    :注：可能存在一句歌词对应多个时轴的情况，故采用二维列表输出
    """
    fs,parts=[],lrc_line.split("]")
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
        fs.append([secfmt, secnum, content, secOrigin])
    return fs

def showInfoDialog(content="",title=""):
    """弹出确认对话框"""
    dlg = wx.MessageDialog(None, content, title, wx.OK)
    dlg.ShowModal()
    dlg.Destroy()
    return False

def getFuzzyMatchingPattern(words:str) -> str:
    """获取words的模糊匹配正则表达式字符串"""
    words = re.sub(r"\s+", "", words)
    pattern = "∷".join(words)
    for k,v in REGEX_CHAR_TRANSFORM_RULES.items():
        pattern = pattern.replace(k, v)
    pattern = "(?i)" + pattern.replace("∷", ".*?")
    return pattern
