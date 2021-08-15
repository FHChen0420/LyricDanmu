# coding: utf-8
import re
from typing import Callable, List, Match, Pattern, Tuple, Union
Replace=Union[str,Callable[[re.Match],str]]

def get_len(string:str) -> int:
    '''获取正则表达式串string的字段宽度'''
    return len(re.sub(r"\[.+?\]","~",string))

def measure(string:str, length:int) -> bool:
    '''判断字符串string中非空格字符数是否小于length'''
    return get_len(string)-string.count(" ")<length

def fill(string:str, length:int) -> str:
    '''填补字符串string，使其中的非空格字符数等于length'''
    dots="\u0592"*(length-get_len(string)+string.count(" "))
    return string+dots

def r_pos(string:str, targets:str) -> int:
    '''查找字符串targets中的字符在字符串string中最后一次出现的位置'''
    r_str=string.replace(" ","")[::-1]
    for index,char in enumerate(r_str):
        if char in targets: return len(r_str)-index-1

def substitute(pat:Pattern,rep:Replace,string:str) -> str:
    '''正则替换函数，是re.sub()的一种修改版本'''
    # 目前有个缺点，如果屏蔽字首尾相同或可拆分为更小的重复单元，则可能无法替换干净。
    # 例如对"ABABA"按"ABA"→"ACA"的替换规则，替换结果为"ACABA"而非"ACACA"。
    def get_min_so(so:Match) -> Match:
        '''递归函数，获取串总长最短的捕获组'''
        new_so=pat.search(so.group()[1:])
        return so if new_so is None else get_min_so(new_so)  
    def min_sub(so:Match) -> str:
        '''回调函数，获取替换结果'''
        min_so=get_min_so(so)
        min_rep=re.sub(r"\\(\d)",lambda x:min_so.group(int(x.group(1))),rep) if isinstance(rep,str) else rep(min_so)
        return so.group().replace(min_so.group(),min_rep)
    return pat.sub(min_sub,string)

def generate_rule(word:str, deal_list:List[Tuple[Pattern,Replace]]) -> None:
    '''根据屏蔽词word，生成相应的匹配模式及替换规则，添加到列表deal_list中'''
    # word中，“#”后的数字表示需要间隔多少个字符才不会被屏蔽。
    # 如果word不含“#”，则默认在第一个字符后添加“\u0592”。
    groups=re.split(r"#[1-9]",word)
    n=len(groups)-1
    if n==0:
        pat = "(?i)" + " ?".join(word)
        rep = lambda x: x.group()[0] + "\u0592" + x.group()[1:]
        deal_list.append((re.compile(pat),rep))
        return
    fills=[int(i) for i in re.findall(r"#([1-9])",word)]
    pat="(?i)" + "".join(["("+groups[i]+".*?)" for i in range(n)]) + "(%s)"%groups[n]
    rep="lambda x: (" + "+".join(["fill(x.group(1),%d)"%(get_len(groups[0])+int(fills[0]))] +
        ["x.group(%d)"%(i+1) for i in range(1,n+1)]) + ") if " + \
        " and ".join(["measure(x.group(%d),%d)"%(i+1,get_len(groups[i])+int(fills[i])) for i in range(n)]) + \
        " else x.group()"
    deal_list.append((re.compile(pat),eval(rep)))

def deal(string:str, deal_list:List[Tuple[Pattern,Replace]]) -> str:
    '''对字符串string按列表deal_list中的匹配模式及替换规则进行反屏蔽处理'''
    # 外部请调用这个函数。
    for i in deal_list:
        string = substitute(i[0], i[1], string)
    return string
