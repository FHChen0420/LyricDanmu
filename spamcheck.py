import re
from typing import Dict

class SpamChecker:

    def __init__(self, spam_regex_string: str = None, uname_regex_string: str = None):
        spam = spam_regex_string
        if not spam:
            with open('full_regex.txt', 'r', encoding='utf-8') as f:
                spam = f.read()
        uname = uname_regex_string
        if not uname:
            with open('uname_regex.txt', 'r', encoding='utf-8') as f:
                uname = f.read()

        self.spam_regex = re.compile(spam)
        self.uname_regex = re.compile(uname)

    def check(self, danmaku: Dict):
        '''
        Check if the given danmaku is a spam danmaku.
        
        This method only takes responsibility for checking whether a danmaku
        is a spam message by its content and author's name. 
        User level spam check should be doing outside.

        :param danmaku dict
            danmaku-like dict
            {
                uname: string, 
                content: string
            }

        :return 
            {
                level: int,
                signature: string
            }

            level:
                0 -> not a spam danmaku
                1 -> content might be a spam danmaku, but its author's name seems legal.
                2 -> is a spam danmaku
            signature:
                the suspicious string. may be used for room word ban list.
        '''
        if 'uname' in danmaku and 'content' in danmaku:
            content_result = self.spam_regex.search(danmaku['content'])
            signature = ''
            if content_result:
                signature = content_result.group(0)
            uname_result = self.uname_regex.search(danmaku['uname'])
            if content_result and uname_result:
                return {
                'level': 2,
                'signature': signature,
            }
            if content_result and (not uname_result):
                return {
                'level': 1,
                'signature': signature,
            }
            return {
                'level': 0,
                'signature': signature,
            }
        else:
            return {
                'level': 0,
                'signature': '',
            }
        
