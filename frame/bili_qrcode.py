import os
from concurrent.futures import ThreadPoolExecutor

import qrcode
import requests
import wx

from utils.api import BiliLiveAPI
from utils.util import logDebug, showInfoDialog


class BiliQrCodeFrame(wx.Frame):
    def __init__(self,parent,acc_no):
        self.oauthKey=""
        self.acc_no=acc_no
        self.blApi=BiliLiveAPI("")
        self.cancel=False
        image=self.GenerateQrCode()
        if not image:   return
        self.ShowFrame(parent,image)
        pool=ThreadPoolExecutor(1,"qrcode")
        pool.submit(self.ThreadOfGetLoginInfo)
        
    def GenerateQrCode(self):
        try:
            data=self.blApi.get_login_url()
            self.oauthKey=data["data"]["oauthKey"]
            qrcode.make(data["data"]["url"]).save("qrcode.tmp")
            return wx.Image("qrcode.tmp",wx.BITMAP_TYPE_PNG).Rescale(300, 300).ConvertToBitmap()
        except requests.exceptions.ConnectionError:
            return showInfoDialog("网络异常，请重试", "生成二维码出错")
        except requests.exceptions.ReadTimeout:
            return showInfoDialog("获取超时，请重试", "生成二维码出错")
        except Exception:
            return showInfoDialog("解析错误，请重试", "生成二维码出错")
    
    def ShowFrame(self,parent,image):
        wx.Frame.__init__(self, parent, title="APP扫码登录", size=(320,320), style=wx.DEFAULT_FRAME_STYLE ^ (wx.RESIZE_BORDER | wx.MAXIMIZE_BOX | wx.MINIMIZE_BOX) |wx.STAY_ON_TOP | wx.FRAME_FLOAT_ON_PARENT)
        panel=wx.Panel(self,size=(320,320),pos=(0,0))
        wx.StaticBitmap(panel, -1, image, pos=(0,0))
        self.Bind(wx.EVT_CLOSE,self.OnClose)
        self.Show()
    
    def ThreadOfGetLoginInfo(self):
        while not self.cancel:
            wx.MilliSleep(1500)
            try:
                data=self.blApi.get_login_info(self.oauthKey)
                if data["data"] in [-4,-5]: # -4=未扫码，-5=已扫码但未确认
                    continue
                elif data["data"]==-2: # -2=链接已过期
                    showInfoDialog("二维码已过期，请重试", "登录失败")
                    break
                else: # 已扫码并完成确认
                    try:
                        session=requests.Session()
                        session.get(url=data["data"]["url"],headers=self.blApi.headers)
                        _dict=session.cookies.get_dict()
                        cookie=f"buvid3={_dict['buvid3']};SESSDATA={_dict['SESSDATA']};bili_jct={_dict['bili_jct']}"
                        self.Parent.SetLoginInfo(cookie,self.acc_no)
                        showInfoDialog("登录成功","提示")
                    except Exception as e:
                        logDebug(f"[QrCode: GetLoginInfo]{e}")
                        showInfoDialog("无法获取登录信息", "登录失败")
                    break
            except requests.exceptions.ConnectionError:
                showInfoDialog("网络异常，请重试", "获取登录信息出错")
                break
            except requests.exceptions.ReadTimeout:
                showInfoDialog("获取超时，请重试", "获取登录信息出错")
                break
            except Exception:
                showInfoDialog("解析错误，请重试", "获取登录信息出错")
                break
        if not self.cancel:
            self.Close()

    def OnClose(self,event):
        self.cancel=True
        self.Show(False)
        if os.path.exists("qrcode.tmp"):
            try: os.remove("qrcode.tmp")
            except: pass
        for btn in self.Parent.btnQrLogins:
            btn.Enable()
        self.Destroy()
