## LyricDanmu
B站直播歌词/同传弹幕发送工具

### 主要功能介绍
##### 歌词相关功能：
+ 基于网易云、QQ音乐API查找歌曲并获取歌词
+ 点击按钮发送歌词弹幕或调整歌词进度，支持自动发送有时轴的歌词，支持同时传双语歌词
+ 支持手动导入歌词至本地库，支持将在线搜索到的歌词添加至收藏库
+ 可编辑本地库与收藏库中的歌词标签，便于搜索
+ 支持快捷发送预设文本
##### 同传相关功能：
+ 可自行设定同传弹幕前缀，发送弹幕时会自动添加
+ 联动模式中，可使用Tab键或Alt+数字键快速切换同传弹幕前缀
+ 可实时显示当前待发送弹幕的文本长度，支持一次性输入2.5倍于当前房间弹幕长度上限的字数
+ 支持对同传数据进行统计，自动导出统计结果csv文件
+ 支持监听直播间的同传弹幕并转发到其他直播间
+ 支持直播追帧，更早地抓取直播流
##### 通用功能：
+ 使用弹幕队列控制弹幕发送间隔，避免弹幕发送频率过快而被拦截
+ 自动将超过长度限制的弹幕进行切割，并分别发送
+ 对b站弹幕屏蔽字进行处理，支持简单的自定义屏蔽处理规则
+ 对部分发送失败的弹幕会自动尝试重发
+ 支持即时查看弹幕发送情况，并将发送过的弹幕与歌名输出到日志文件中
+ 支持设置在当前直播间的弹幕颜色与位置

### Pyinstaller打包指令
+ Windows(64位)：

    ```pyinstaller -F -w MainFrame.pyw -n LyricDanmu --add-data "./chaser/static/*;./chaser/static" --add-data "./dll/x64/*;."```

+ MacOS(M1芯片可能会存在打包失败的情况，请尝试使用Rosetta运行)：

    ```pyinstaller -F -w MainFrame.pyw -n LyricDanmu --add-data "./chaser/static/*:./chaser/static"```

### 代码列表
开发环境：Windows Python3.8.10 / MacOS Python3.9.1 universal2
第三方库：见[requirements.txt](https://github.com/FHChen0420/LyricDanmu/blob/main/requirements.txt)

+ MainFrame.pyw 主界面
+ SongSearchFrame.py 歌词搜索结果界面
+ SongMarkFrame.py 歌词收藏设置界面
+ RoomSelectFrame.py 直播间选择界面（用于进入房间）
+ SpRoomSelectFrame.py 直播间选择界面（用于转发弹幕）
+ DanmuSpreadFrame.py 弹幕转发配置界面
+ LiveUserSearchFrame.py 直播用户搜索界面
+ GeneralConfigFrame.py 应用通用设置界面
+ ShieldConfigFrame.py 屏蔽词管理界面
+ CustomTextFrame.py 预设文本界面
+ RecordFrame.py 弹幕发送记录界面
+ ColorFrame.py 弹幕颜色选择框
+ PlayerFrame.py 直播画面播放窗体
+ API.py 接口类
+ BiliLiveAntiShield.py B站直播屏蔽字处理类
+ BiliLiveWebSocket.py B站直播websocket类
+ util.py 工具函数
+ constant.py 常量
+ langconv.py & zh_wiki.py 繁体转简体逻辑&数据（Ref: [skydark/nstools](https://github.com/skydark/nstools)）
+ chaser/ B站直播追帧本地服务（Ref: [tsingsee/EasyPlayer.js](https://github.com/tsingsee/EasyPlayer.js)）

```注意：本项目的文件命名、变量命名并不规范，请勿模仿```
