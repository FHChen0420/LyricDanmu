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
    """将时间戳ts按fmt格式转化为字符串，ms表示ts是否为毫秒级时间戳"""
    if ts is None:  ts=time.time()
    elif ms:        ts=ts/1000
    return time.strftime(fmt,time.localtime(ts))

def strToTs(string,fmt="%y-%m-%d %H:%M:%S") -> int:
    """将字符串string按fmt格式转化为秒级时间戳"""
    return int(time.mktime(time.strptime(string,fmt)))

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

def updateCsvFile(file_path:str,key_index:int,new_records:dict,max_size:int=1024):
    """更新csv文件的结尾部分（修改原有记录或新增记录）
    
    :param: file_path  CSV文件路径
    :param: key_index  数据项的键值在CSV文件中的列编号
    :param: new_records  待更新项的字典，每项为 键值：数据项整行的文本数据
    :param: max_size  从CSV文件结尾开始，允许向前读取并修改的最大字节数"""
    try:
        with open(file_path, "r+b") as f:
            f.seek(0,2)
            read_size = block_size = min(max_size, f.tell())
            f.seek(-block_size,2)
            if block_size==max_size: read_size = block_size-f.read().index(b'\n')-1
            f.seek(-read_size,2)
            content=str(f.read(),encoding="utf-8").strip()
            f.seek(-read_size,2)
            f.truncate()
        old_lines,old_records=[],{}
        if content!="": old_lines=content.strip().split("\n")
        for i,v in enumerate(old_lines):
            line_items=v.strip().split(",")
            if len(line_items)>key_index:
                old_records[line_items[key_index]]=v
            else:   old_records[i]=v
        with open(file_path, "a", encoding="utf-8") as f:
            for k,v in old_records.items():
                if k in new_records.keys():
                    f.write(new_records[k].strip()+"\n")
                else: f.write(v.strip()+"\n")
            for k,v in new_records.items():
                if k not in old_records.keys():
                    f.write(v.strip()+"\n")
    except Exception as e: raise e
