import abc
import hashlib
import json
import threading
import time

import requests


def get_UA():
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                     "Chrome/118.0.0.0 Safari/537.36 Edg/118.0.2088.61"
    }


class AutoExpireInterface(abc.ABC):
    __refresh_time: int
    __data = {}
    __next_refresh_time: int
    __refresh_lock = threading.Lock()

    def __init__(self, refresh_time: int):
        self.__refresh_time = refresh_time
        self.__next_refresh_time = 0

    async def refresh(self, **kwargs):
        pass

    async def get(self, **kwargs):
        with self.__refresh_lock:
            cur_time = int(time.time())
            if cur_time > self.__next_refresh_time:
                try:
                    self.__data = await self.refresh(**kwargs)
                except... as e:
                    print(f"refresh fail !error {e}")
                self.__next_refresh_time = cur_time + self.__refresh_time
        return self.__data


def get_mixin_key(img_key, sub_key):
    key = img_key + sub_key
    mixin_key = ''.join([key[i] for i in
                         [46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
                          27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
                          37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4, 22,
                          25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 34, 44, 52]][:32])
    return mixin_key


class WbiKey(AutoExpireInterface):
    async def refresh(self, **kwargs):
        # 这里未登录（不提供session）也可以
        wbi_res = requests.get("https://api.bilibili.com/x/web-interface/nav", **{
                        "headers": get_UA()})
        if wbi_res.status_code != 200:
            print(f"WbiKey refresh fail. status_code = {wbi_res.status_code}")
        wei_data = json.loads(wbi_res.text)["data"]
        data = {
            "img_url": wei_data["wbi_img"]["img_url"].rsplit("/", 1)[1].split(".")[0],
            "sub_url": wei_data["wbi_img"]["sub_url"].rsplit("/", 1)[1].split(".")[0]
        }
        print(f"refresh wbi key success. wbi_key = {data}")
        return data


wbi_key = WbiKey(86400)


async def fill_wrid_wts(params):
    wbi_key_data = await wbi_key.get()
    img_key, sub_key = wbi_key_data["img_url"], wbi_key_data["sub_url"]
    mixin_key = get_mixin_key(img_key, sub_key)
    wts = int(time.time())
    data = {
        "wts": wts
    }
    data.update(params)
    dst_key = '&'.join(f'{k}={v}' for k, v in sorted(data.items())) + mixin_key

    w_rid = hashlib.md5(dst_key.encode(encoding="utf-8")).hexdigest()
    params["w_rid"] = w_rid
    params["wts"] = wts
