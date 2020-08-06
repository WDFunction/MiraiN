import hashlib
import json
import os
import re
import subprocess
import sys
from typing import Callable
from urllib.request import urlopen


def detect_java() -> bool:
    try:
        subprocess.Popen("java", stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        return False
    return True


def __checker(fl: dict, dr: str):
    for k, v in fl.items():
        if isinstance(v, list):
            path = os.path.join(dr, f'{k}-{v[0]}.jar')
            if not os.path.isfile(path):
                download_file(v[1], path)
            else:
                continue
        elif isinstance(v, dict):
            path = os.path.join(dr, k)
            if not os.path.isdir(path):
                os.mkdir(path)
            __checker(v, os.path.join(dr, path))
        else:
            pass


def check_update():
    print("Checking update")
    try:
        conn = urlopen("https://mirai.nullcat.cn/update_check")
    except ConnectionError as e:
        print("Unable to connect to update server:", e)
        return False
    try:
        __checker(json.loads(conn.read()), "")
        if not os.path.isfile("content/.wrapper.txt"):
            print("generate .wrapper.txt")
            with open("content/.wrapper.txt", "wb") as f:
                f.write(b"Pure")
    except Exception as e:
        print("Update Failed:", e)
    print("Update complete")
    return True


def download_file(url: str, path: str):
    print("Downloading file to", path)
    conn = urlopen(url)
    if "Content-Length" not in conn.headers:
        raise ConnectionError("Content-Length not found")
    length = int(conn.headers["Content-Length"])
    print(f"File size: {length} ({round(length / 1048576, 2)}MB)")
    with open(path, "wb") as f:
        nl = length
        while True:
            blk = conn.read(4096)
            if not blk:
                break
            nl -= len(blk)
            progress_bar(100 - int((nl / length) * 100), 4)
            f.write(blk)
        print("")


def gen_word(count: int, w: str) -> str:
    return "".join([w for _ in range(count)])


def progress_bar(present: int, resize: int = 1):
    size = 100 // resize
    if not present:
        out = f'\r[{gen_word(size, " ")}] {present}%'
    else:
        out = f'\r[{gen_word(present // resize, "=")}{gen_word(size - present // resize, " ")}] {present}%'
    sys.stdout.write(out)
    sys.stdout.flush()


def verify_file(path: str, sig: str, method=None) -> bool:
    if not method:
        method = hashlib.md5()
    with open(path, "rb") as f:
        while True:
            data = f.read(16384)
            if data:
                method.update(data)
            else:
                break
    if method.hexdigest() == sig:
        return True
    return False


def qt(prefix: str, bind_func: Callable):
    def __inner(data: str):
        e = re.search(prefix + r"\((.+?)\)", data)
        if e:
            info = {}
            for _ in e.group(1).split(", "):
                k, v = _.split("=", 1)
                info[k] = v
            return bind_func(info)

    return __inner


def nt(rule: str, bind_func: Callable):
    def __inner(data: str):
        e = re.search(rule, data)
        if e:
            return bind_func(e)

    return __inner


class MiraiManager:
    def __init__(self, mcon_path: str):
        self.__process = subprocess.Popen(["java", "-jar", mcon_path, "--update", "keep"],
                                          stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def _readline(self) -> bytes:
        line = self.__process.stdout.readline().rstrip(b"\r\n")
        if line and line[0] == 27:
            return line[5:-8]
        else:
            return line

    def command_execute(self, cm: str, *args):
        self.__process.stdin.write(f"{cm} {' '.join(args)}\n".encode())
        self.__process.stdin.flush()

    def listen(self, handlers=None):
        if not handlers:
            handlers = []
        while not self.__process.poll():
            data = self._readline().decode("gbk", errors="ignore")
            print(data)
            for handle in handlers:
                if handle(data):
                    break

    def login(self, qq_num: str, password: str):
        self.command_execute("login", qq_num, password)

    def kill_process(self):
        self.__process.kill()

    def close(self):
        from signal import SIGTERM
        self.__process.send_signal(SIGTERM)  # Ctrl+C
        self.__process.wait()
