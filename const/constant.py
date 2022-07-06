from enum import Enum

# 发送队列检测间隔（毫秒）
FETCH_INTERVAL_MS = 30

# 屏蔽词库更新间隔（秒）
GLOBAL_SHIELDS_UPDATE_INTERVAL_S = 3600

# 长间隔歌词检测阈值（秒）
LYRIC_EMPTY_LINE_THRESHOLD_S = 12

# B站直播弹幕颜色编号
BILI_COLORS = {
    '16777215': '白色', '14893055': '紫色', '5566168': '松石绿', '5816798': '雨后蓝', '4546550': '星空蓝', 
    '9920249': '紫罗兰', '12802438': '梦境红', '16747553': '热力橙', '16774434': '香槟金', '16738408': '红色', 
    '6737151': '蓝色', '65532': '青色', '16772431': '黄色', '16766720': '盛典金', '4286945': '升腾蓝', 
    '8322816': '绿色', '16750592': '橙色', '16741274': '粉色'
}

# B站直播弹幕位置编号及显示
BILI_MODES = {'1':'⋘', '4':'▁▁', '5':'▔▔'}

# 转义处理规则
HTML_TRANSFORM_RULES = {
    r"&apos;": "'",
    r"&quot;": "\"",
    r"&amp;": "＆",
    r"&nbsp;|\u00A0": " ",
}

# 压缩处理规则
COMPRESS_RULES = {
    r"[\.・]{2,}": "…",
    r"[!！]{2,}": "‼",
    r"[\?？]{2,}": "⁇",
    r"(。|，|\.|,)$": "",
    # 连续空格已在屏蔽字处理中进行了压缩，这里不再重复处理
}

# 文件名特殊字符处理规则
FILENAME_TRANSFORM_RULES = {
    "/":"／", "\\":"＼", "|":"｜", "*":"＊", "?":"？",
    ":":"：", "<":"＜", ">":"＞", "\"":"“",
}

# 中文歌词补充处理规则
CN_LYRIC_PREPROCESS_RULES = {
    "妳":"你",
    "(?<![名巨显昭卓译编土原执])著(?![称有名作述于书籍])": "着",
    #"(?<![包缠妆])裏(?![着在住足尸])": "里", # 偶尔会遇到"裏"(li)错写成"裹"(guo)的情况
    r"[\(（].*?[译注]\s*?[:：].*?[\)）]": "",
}

# 可忽略的歌词规则
LYRIC_IGNORE_RULES=r"(?i)^[^\w\u4e00-\u9fff\u3040-\u31ff]{0,3}(终|完|undefined|[终終お]わ(る|り|った)|end|fin|music|[伴间]奏)[^\w\u4e00-\u9fff\u3040-\u31ff]{0,3}$|.(:|：|︰| - ).|©|不得翻唱"

# 恋口上默认预设
DEFAULT_CUSTOM_TEXT="<texts>\n<text title=\"古守恋口上\">\n「我有些话想要对你说」\n「古守实在是太可爱了」\n「喜欢喜欢超喜欢 果然喜欢」\n「好不容易找到的吸血鬼」\n「肉肉来到世上的理由」\n「就是为了和古守相遇」\n「和肉肉一起共度一生」\n「世界上第一的家里蹲」\n</text>\n</texts>"

class DanmuCode(Enum):
    """自定义弹幕发送结果状态码"""
    # 对应信息见后续代码中的ERR_INFO
    SUCCESS         = "0"
    GLOBAL_SHIELDED = "1"
    ROOM_SHEILDED   = "2"
    HIGH_FREQ       = "3"
    REPEATED        = "4"
    SWALLOWED       = "5"
    MAX_LIMIT       = "6"
    NOT_LOGIN       = "7"
    FAIL            = "x"
    NETWORK_ERROR   = "A"
    TIMEOUT_ERROR   = "B"
    CONNECT_CLOSE   = "C"
    REQUEST_ERROR   = "X"
    CANCELLED       = "Z"
    SHIELDED_RE     = "1+"
    HIGH_FREQ_RE    = "3+"
    SWALLOWED_RE    = "5+"
    MAX_LIMIT_RE    = "6+"
    INFO            = "-"

# 弹幕状态码对应的描述、弹幕记录颜色
ERR_INFO={
    DanmuCode.SUCCESS:          ("", "black"),
    DanmuCode.GLOBAL_SHIELDED:  ("🚫 全局屏蔽⋙ ", "red"),
    DanmuCode.ROOM_SHEILDED:    ("🚫 房间屏蔽⋙ ", "red"),
    DanmuCode.HIGH_FREQ:        ("⛔ 频率过快⋙ ", "gold"),
    DanmuCode.REPEATED:         ("⛔ 重复发送⋙ ", "gold"),
    DanmuCode.SWALLOWED:        ("⛔ 弹幕被吞⋙ ", "gold"),
    DanmuCode.MAX_LIMIT:        ("⛔ 房间弹幕过密⋙ ", "gold"),
    DanmuCode.NOT_LOGIN:        ("🔑 账号无效⋙ ", "gold"),
    DanmuCode.FAIL:             ("❌ 发送失败⋙ ", "gold"),
    DanmuCode.NETWORK_ERROR:    ("🌐 网络异常⋙ ", "gold"),
    DanmuCode.TIMEOUT_ERROR:    ("⏳ 请求超时⋙ ", "gold"),
    DanmuCode.CONNECT_CLOSE:    ("🌐 远程连接异常关闭⋙ ", "gold"),
    DanmuCode.REQUEST_ERROR:    ("🌐 请求错误⋙ ", "red"),
    DanmuCode.CANCELLED:        ("❌ 取消发送⋙ ", "gray"),
    DanmuCode.SHIELDED_RE:      ("🔄 屏蔽句重发", "gray"),
    DanmuCode.HIGH_FREQ_RE:     ("🔄 频率过快", "gray"),
    DanmuCode.SWALLOWED_RE:     ("🔄 弹幕被吞", "gray"),
    DanmuCode.MAX_LIMIT_RE:     ("🔄 房间弹幕过密", "gray"),
    DanmuCode.INFO:             ("", "gray"),
}

class DanmuSrc(Enum):
    """弹幕来源类型"""
    COMMENT     = "0"       # 弹幕输入框
    LYRIC       = "1"       # 歌词
    CUSTOM_TEXT = "2"       # 预设文本
    SPREAD      = "3"       # 同传转发