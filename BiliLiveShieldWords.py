# coding: utf-8
import re

def get_len(string):
    # 获取字符串string的长度
    # 在len()的基础上，[]及其中的内容统一视为一个字符。
    return len(re.sub(r"\[.+?\]","~",string))

def measure(string,length):
    # 判断字符串string中非空格字符数是否小于length
    return get_len(string)-string.count(" ")<length

def fill(string,length):
    # 填补字符串string，使其中的非空格字符数等于length
    dots="\u0592"*(length-get_len(string)+string.count(" "))
    return string.rstrip()+dots

def r_pos(string,targets):
    # 查找字符串targets中的字符在字符串string中最后一次出现的位置
    r_str=string.replace(" ","")[::-1]
    for index,char in enumerate(r_str):
        if char in targets: return len(r_str)-index-1

def substitute(pat,rep,string):
    # 正则替换函数（仅基于本代码的逻辑对re.sub()进行改进）
    # 目前有个缺点，如果屏蔽字首尾部分相同，则可能无法替换干净。例如对"ABABA"按"ABA"→"ACA"的替换规则，
    # 替换结果为"ACABA"而非"ACACA"。目前B站这类屏蔽字比较少，如535，爸爸，啪啪 等。
    def get_min_so(so):
        # 递归函数，获取串总长最短的捕获组
        new_so=re.search(pat,so.group()[1:])
        return so if new_so is None else get_min_so(new_so)  
    def min_sub(so):
        # 回调函数，获取替换结果
        min_so=get_min_so(so)
        min_rep=rep if isinstance(rep,str) else rep(min_so)
        return so.group().replace(min_so.group(),min_rep)
    return re.sub(pat,min_sub,string)

def generate_rule(word,rules):
    # 根据屏蔽词word，生成相应的处理规则
    # word中，“#”后的数字表示需要间隔多少个字符才不会被屏蔽
    # 如果word不含“#”，则默认在第一个字符后添加“\u0592”
    try:
        groups=re.split(r"#[1-9]",word)
        n=len(groups)-1
        if n==0:
            pat = "(?i)" + " ?".join(word)
            rep = word[0] + "\u0592" + word[1:]
            rules[pat] = rep
            return
        fills=[int(i) for i in re.findall(r"#([1-9])",word)]
        pat="(?i)" + "".join(["("+groups[i]+".*?)" for i in range(n)]) + "(%s)"%groups[n]
        rep="lambda x: (" + "+".join(["fill(x.group(1),%d)"%(get_len(groups[0])+int(fills[0]))] +
            ["x.group(%d)"%(i+1) for i in range(1,n+1)]) + ") if " + \
            " and ".join(["measure(x.group(%d),%d)"%(i+1,get_len(groups[i])+int(fills[i])) for i in range(n)]) + \
            " else x.group()"
        rules[pat] = eval(rep)
    except Exception as e:
        pass

def deal(string,rules):
    # 对字符串string进行反屏蔽处理
    # 外部请调用这个函数
    string=re.sub(r" +"," ",string) # 合并连续半角空格
    for k, v in rules.items():
        string = substitute(k, v, string)
    return string
