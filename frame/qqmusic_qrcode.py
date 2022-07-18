import os
from threading import Thread

import requests
import wx

from utils.api import QQMusicAPI
from utils.util import showInfoDialog


class QQMusicQrCodeFrame(wx.Frame):
    def __init__(self,parent):
        self.qqApi:QQMusicAPI=parent.qqApi
        self.cancel=False
        parent.qq_lock=True
        image=self.GenerateQrCode()
        if not image:   return
        self.ShowFrame(parent,image)
        Thread(target=self.ThreadOfGetLoginInfo,daemon=True).start()
        
    def GenerateQrCode(self):
        try:
            self.qqApi._xlogin()
            resp=self.qqApi.get_login_qrcode()
            with open("qrcode_q.tmp","wb") as f:
                f.write(resp.content)
            return wx.Image("qrcode_q.tmp",wx.BITMAP_TYPE_PNG).Rescale(300, 300).ConvertToBitmap()
        except requests.exceptions.ConnectionError:
            return showInfoDialog("网络异常，请重试", "生成二维码出错")
        except requests.exceptions.ReadTimeout:
            return showInfoDialog("获取超时，请重试", "生成二维码出错")
        except Exception as e:
            print(e)
            return showInfoDialog("解析错误，请重试", "生成二维码出错")
    
    def ShowFrame(self,parent,image):
        wx.Frame.__init__(self, parent, title="扫码登录QQ音乐", size=(320,320), style=wx.DEFAULT_FRAME_STYLE ^ (wx.RESIZE_BORDER | wx.MAXIMIZE_BOX | wx.MINIMIZE_BOX) |wx.STAY_ON_TOP | wx.FRAME_FLOAT_ON_PARENT)
        panel=wx.Panel(self,size=(320,320),pos=(0,0))
        wx.StaticBitmap(panel, -1, image, pos=(0,0))
        self.Bind(wx.EVT_CLOSE,self.OnClose)
        self.Show()
    
    def ThreadOfGetLoginInfo(self):
        while not self.cancel:
            wx.MilliSleep(1500)
            try:
                resp=self.qqApi.get_login_info()
                data=eval(resp.text[6:])
                code=data[0] # 65已过期, 66未扫码, 67已扫码待确认
                if code in ('66','67'):
                    continue
                elif code == '65':
                    showInfoDialog("二维码已过期，请重试", "登录失败")
                elif code=='0': # 已扫码并完成确认
                    try:
                        self.qqApi.authorize(data[2])
                        showInfoDialog("登录成功","提示")
                    except:
                        showInfoDialog("签名认证失败，请重试","登录失败")
                else:
                    showInfoDialog("扫码出现问题，请重试","登录失败")
                break
            except requests.exceptions.ConnectionError:
                showInfoDialog("网络异常，请重试", "获取登录信息出错")
                break
            except requests.exceptions.ReadTimeout:
                showInfoDialog("获取超时，请重试", "获取登录信息出错")
                break
            except Exception as e:
                print(e)
                showInfoDialog("解析错误，请重试", "获取登录信息出错")
                break
        if not self.cancel:
            self.Close()

    def OnClose(self,event):
        self.cancel=True
        self.Show(False)
        if os.path.exists("qrcode_q.tmp"):
            try: os.remove("qrcode_q.tmp")
            except: pass
        self.Parent.qq_lock=False
        self.Destroy()
