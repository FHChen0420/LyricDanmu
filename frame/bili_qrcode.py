import os
from threading import Thread

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
        Thread(target=self.ThreadOfGetLoginInfo,daemon=True).start()
        
    def GenerateQrCode(self):
        try:
            data=self.blApi.get_login_url()
            self.oauthKey=data["data"]["qrcode_key"]
            qrcode.make(data["data"]["url"]).save("qrcode_b.tmp")
            return wx.Image("qrcode_b.tmp",wx.BITMAP_TYPE_PNG).Rescale(300, 300).ConvertToBitmap()
        except requests.exceptions.ConnectionError:
            return showInfoDialog("网络异常，请重试", "生成二维码出错")
        except requests.exceptions.ReadTimeout:
            return showInfoDialog("获取超时，请重试", "生成二维码出错")
        except Exception:
            return showInfoDialog("解析错误，请重试", "生成二维码出错")
    
    def ShowFrame(self,parent,image):
        wx.Frame.__init__(self, parent, title="扫码登录哔哩哔哩", size=(320,320), style=wx.DEFAULT_FRAME_STYLE ^ (wx.RESIZE_BORDER | wx.MAXIMIZE_BOX | wx.MINIMIZE_BOX) |wx.STAY_ON_TOP | wx.FRAME_FLOAT_ON_PARENT)
        panel=wx.Panel(self,size=(320,320),pos=(0,0))
        wx.StaticBitmap(panel, -1, image, pos=(0,0))
        self.Bind(wx.EVT_CLOSE,self.OnClose)
        self.Show()
    
    def ThreadOfGetLoginInfo(self):
        while not self.cancel:
            wx.MilliSleep(1500)
            try:
                data=self.blApi.get_login_info(self.oauthKey)
                state_code = data["data"]["code"]
                if state_code in [86101, 86090]: # 86101=未扫码，86090=已扫码但未确认
                    continue
                elif state_code == 86038: # 86038=链接已过期
                    showInfoDialog("二维码已过期，请重试", "登录失败")
                    break
                elif state_code == 0: # 已扫码并完成确认
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
                else:
                    showInfoDialog(f"未知的状态码:{state_code}\n信息:{data['data']['message']}\n\n（请向工具作者反馈）", "获取登录信息出错")
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
        if os.path.exists("qrcode_b.tmp"):
            try: os.remove("qrcode_b.tmp")
            except: pass
        for btn in self.Parent.btnQrLogins:
            btn.Enable()
        self.Destroy()
