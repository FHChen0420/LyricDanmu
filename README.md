## LyricDanmu
B站直播歌词/同传弹幕发送工具

开发环境：Python3.9.1

### 代码列表

+ MainFrame.pyw 主界面
+ SongSearchFrame.py 歌词搜索结果界面
+ SongMarkFrame.py 歌词收藏设置界面
+ RoomSelectFrame.py 直播间选择界面
+ GeneralConfigFrame.py 应用通用设置界面
+ ShieldConfigFrame.py 屏蔽词管理界面
+ CustomTextFrame.py 预设文本界面
+ RecordFrame.py 弹幕发送记录界面
+ ColorFrame.py 弹幕颜色选择框
+ PlayerFrame.py 直播画面播放窗体
+ API.py 接口类
+ BiliLiveAntiShield.py 屏蔽字处理
+ util.py 工具函数
+ constant.py 常量
+ langconv.py & zh_wiki.py 繁体转简体逻辑&数据（Ref: skydark/nstools）
+ chaser/ B站直播追帧本地服务（By:Sirius   Ref: bilibili/flv.js）

### Pyinstaller打包指令

+ Windows(64位)：

    ```pyinstaller -F -w MainFrame.pyw -n LyricDanmu --add-data "./chaser/static/*;./chaser/static" --add-data "./dll/x64/*;."```

+ MacOS：

    ```pyinstaller -F -w MainFrame.pyw -n LyricDanmu --add-data ./chaser/static/*:./chaser/static```