import wx

class AutoPanel(wx.Panel):
    def __init__(self, parent, orient = wx.HORIZONTAL, spacing = 0):
        super().__init__(parent)
        self.__spacing = spacing
        self.__sizer = wx.BoxSizer(orient)
        self.SetSizer(self.__sizer)

    def AddToSizerWithoutSpacing(self, control, *args, **kw):
        self.__sizer.Add(control, *args, **kw)
        return control
    
    def AddToSizer(self, control, *args, **kw):
        if self.__sizer.GetItemCount() > 0:
            self.__sizer.AddSpacer(self.__spacing)
        return self.AddToSizerWithoutSpacing(control, *args, **kw)
    
    def AddSpacing(self, spacing = 0):
        self.__sizer.AddSpacer(spacing)
