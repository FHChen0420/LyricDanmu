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
+ 支持B站APP扫码登录
+ 使用弹幕队列控制弹幕发送间隔，避免弹幕发送频率过快而被拦截
+ 自动将超过长度限制的弹幕进行切割，并分别发送
+ 对b站弹幕屏蔽字进行处理，支持简单的自定义屏蔽处理规则
+ 对部分发送失败的弹幕会自动尝试重发
+ 支持即时查看弹幕发送情况，并将发送过的弹幕与歌名输出到日志文件中
+ 支持设置在当前直播间的弹幕颜色与位置

### Pyinstaller打包指令
+ Windows(64位)：

    ```pyinstaller -F -w app.pyw -n LyricDanmu --add-data "./static/*;./static" --add-data "./dll/x64/*;."```

+ MacOS(M1芯片可能会存在打包失败的情况，请尝试使用Rosetta运行)：

    ```pyinstaller -F -w app.pyw -n LyricDanmu --add-data "./static/*:./static"```

### 项目结构
开发环境：Windows Python3.8.10 / MacOS Python3.9.1 universal2

第三方库：见[requirements.txt](https://github.com/FHChen0420/LyricDanmu/blob/main/requirements.txt)

主要代码：

```
│  app.pyw                      程序入口
│          
├─const                         <常量目录>
│  │  constant.py               自定义常量类
│  │  zh_wiki.py                汉字简繁转化数据
│          
├─frame                         <界面目录>
│  │  bili_qrcode.py            扫码登录界面
│  │  color_select.py           弹幕颜色选择界面
│  │  custom_text.py            预设文本发送界面
│  │  danmu_record.py           弹幕发送记录界面
│  │  danmu_spread.py           弹幕转发配置界面
│  │  general_config.py         应用设置界面
│  │  liveroom_search.py        直播间搜索界面
│  │  live_player.py            直播画面播放界面
│  │  main.py                   主界面
│  │  qqmusic_qrcode.py         QQ音乐扫码登录界面
│  │  room_select.py            进入房间选择界面
│  │  shield_config.py          屏蔽词管理界面
│  │  song_mark.py              歌词收藏设置界面
│  │  song_search.py            歌词搜索结果界面
│  │  spread_room_select.py     转发房间选择界面
│      
├─utils                         <工具目录>
│  │  api.py                    接口类
│  │  langconv.py               汉字简繁转化工具
│  │  live_anti_shield.py       B站直播弹幕屏蔽词处理工具
│  │  live_chaser.py            B站直播追帧工具
│  │  live_websocket.py         B站直播websocket工具
│  │  util.py                   自定义工具类
```

引用项目：

+ B站直播弹幕屏蔽词处理工具：[FHChen0420/bili_live_shield_words](https://github.com/FHChen0420/bili_live_shield_words)
+ 汉字简繁转化工具：[skydark/nstools](https://github.com/skydark/nstools)
+ 视频直播播放器：[tsingsee/EasyPlayer.js](https://github.com/tsingsee/EasyPlayer.js)

```注意：本项目的函数命名、变量命名并不规范，请勿模仿```
