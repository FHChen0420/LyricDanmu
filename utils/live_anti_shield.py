# coding:utf-8
import re
from typing import Callable, Dict, List, Match, Pattern, Tuple, Union  


Replace=Union[str,Callable[[Match],str]]

class BiliLiveAntiShield:
    def __init__(self,rules:Dict[str,Replace],words:List[str],filler:str="\U000E0020"):
        '''B站直播弹幕反屏蔽工具
        
        :param: rules 正则处理字典[正则匹配串:正则捕获处理函数/字符串]（用于处理较复杂规则）
        :param: words 屏蔽词列表（用于处理较简单规则）
        :param: filler 用于填充屏蔽词的单字符，默认为U+E0020'''
        self.__filler=filler
        self.__single_fill=lambda x: x.group()[0]+self.__filler+x.group()[1:]
        self.__multi_fill=tuple([lambda x,i=i: x.group(1)+self.__fill(x.group(2),i) for i in range(10)])
        self.__deal_list:List[Tuple[Pattern,Replace]]=[]
        for pat,rep in rules.items():
            try:    self.__deal_list.append((re.compile(pat),rep))
            except: continue
        for word in words:
            self.__generate_rule(word)

    def __fill(self,string:str,length:int) -> str:
        '''使用填充符来填补字符串string，使其中的非空格字符数等于length'''
        dots=self.__filler*(length-len(string)+string.count(" "))
        return string+dots

    def __generate_rule(self,word:str) -> None:
        '''根据屏蔽词word，生成相应的匹配模式及替换规则，添加到列表deal_list中'''
        # word中，“#”后的数字表示至少需要间隔多少个非空格字符才不会被屏蔽。
        # 如果word不含“#”，则在第一个字符后添加一个填充符来进行处理。
        try:
            parts=re.split(r"#[1-9]",word)
            n=len(parts)-1
            if n==0:
                pat = "(?i)"+" ?".join(word)
                self.__deal_list.append((re.compile(pat),self.__single_fill))
                return
            distance=[int(i) for i in re.findall(r"#([1-9])",word)]
            regex1,regex2="",""
            if distance[0]==1:
                regex1=" ?"
            else:
                if parts[0][0]=="[":    exclude_chars=parts[0][1:-1]
                else: exclude_chars=parts[0] if len(parts[0])==1 else ""
                regex1="(?: ?[^\s%s]){0,%d}? ?"%(exclude_chars,distance[0]-1)
            for i in range(1,n):
                regex=" ?" if distance[i]==1 else "(?: ?\S){0,%d} ?"%(distance[i]-1)
                regex2+=regex+parts[i+1]
            pat="(?i)(%s)(%s)(?=%s)"%(parts[0],regex1,parts[1]+regex2)
            self.__deal_list.append((re.compile(pat),self.__multi_fill[distance[0]]))
        except: pass

    def deal(self,string:str) -> str:
        '''对字符串string进行反屏蔽处理'''
        for i in self.__deal_list:
            try:    string = i[0].sub(i[1],string)
            except: continue
        return string
