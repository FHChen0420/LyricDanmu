# coding:utf-8
import re
from typing import Callable, Match, Pattern, Union
Replace=Union[str,Callable[[Match],str]]

def get_len(string:str) -> int:
    '''获取正则表达式串string的字段宽度'''
    return len(re.sub(r"\[.+?\]","~",string))

def measure(string:str,length:int) -> bool:
    '''判断字符串string中非空格字符数是否小于length'''
    return get_len(string)-string.count(" ")<length

def fill(string:str,length:int) -> str:
    '''填补字符串string，使其中的非空格字符数等于length'''
    dots="\u0592"*(length-get_len(string)+string.count(" "))
    return string+dots

class BiliLiveAntiShield:
    def __init__(self,rules:dict[str,Replace],words:list[str]):
        '''B站直播弹幕反屏蔽工具
        
        :param: rules 正则处理字典[正则匹配串:正则捕获处理函数/字符串]（用于处理较复杂规则）
        :param: words 屏蔽词列表（用于处理较简单规则）'''
        self.__deal_list:list[tuple[Pattern,Replace]]=[]
        for pat,rep in rules.items():
            self.__deal_list.append((re.compile(pat),rep))
        for word in words:
            self.__generate_rule(word)
    
    def __substitute(self,pat:Pattern,rep:Replace,string:str) -> str:
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

    def __generate_rule(self,word:str) -> None:
        '''根据屏蔽词word，生成相应的匹配模式及替换规则，添加到列表deal_list中'''
        # word中，“#”后的数字表示需要间隔多少个字符才不会被屏蔽。
        # 如果word不含“#”，则默认在第一个字符后添加“\u0592”。
        groups=re.split(r"#[1-9]",word)
        n=len(groups)-1
        if n==0:
            pat = "(?i)" + " ?".join(word)
            rep = lambda x: x.group()[0] + "\u0592" + x.group()[1:]
            self.__deal_list.append((re.compile(pat),rep))
            return
        fills=[int(i) for i in re.findall(r"#([1-9])",word)]
        pat="(?i)" + "".join(["("+groups[i]+".*?)" for i in range(n)]) + "(%s)"%groups[n]
        rep="lambda x: (" + "+".join(["fill(x.group(1),%d)"%(get_len(groups[0])+int(fills[0]))] +
            ["x.group(%d)"%(i+1) for i in range(1,n+1)]) + ") if " + \
            " and ".join(["measure(x.group(%d),%d)"%(i+1,get_len(groups[i])+int(fills[i])) for i in range(n)]) + \
            " else x.group()"
        self.__deal_list.append((re.compile(pat),eval(rep)))

    def deal(self,string:str) -> str:
        '''对字符串string进行反屏蔽处理'''
        for i in self.__deal_list:
            string = self.__substitute(i[0], i[1], string)
        return string