import os
import re
import sys
import json
import shutil
import hashlib
import tarfile
import zipfile
import subprocess
from typing import Callable, Union
from urllib.request import urlopen


if sys.platform == "win32":  # <- Special version
    encode_type = "gbk"
else:
    encode_type = "utf-8"


def fuzzy_get(pattern: str, path: str = ".") -> Union[str, None]:
    for n in os.listdir(path):
        if re.match(pattern, n):
            return n


def extract_all(target: str, output_path: str = ".") -> bool:
    if target.endswith(".gz"):
        executor = tarfile.open
    elif target.endswith(".zip"):
        executor = zipfile.ZipFile
    else:
        raise ValueError("Unknown file type {}".format(target.rsplit(".", 1)[1]))
    try:
        with executor(target) as tf:
            tf.extractall(output_path)
        return True
    except Exception as e:
        print(f"{target}: {e}")
        return False


def get_java_path() -> Union[str, None]:
    path = shutil.which("java")
    if not path:
        java_home = fuzzy_get(r"(jdk|jre)-(.*)")
        if java_home:
            if os.path.join(java_home, "bin/java.exe"):
                return os.path.join(java_home, "bin/java.exe")
        return None
    else:
        return path


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
        return False
    print("Update complete")
    return True


def get_java() -> bool:
    try:
        dl = json.loads(urlopen("https://mirai.nullcat.cn/update_jre").read())
    except ConnectionError as e:
        print("Unable to connect to update server:", e)
        return False
    if sys.platform in dl:
        save_path = f"jdk_bin.{dl[sys.platform].rsplit('.', 1)[1]}"
        if not os.path.isfile(save_path):
            if not download_file(dl[sys.platform], save_path):
                return False
        print("Extract jre...")
        if extract_all(save_path):
            print("Done")
            return True
        else:
            print("Extract failed")
            return False


def download_file(url: str, path: str):
    print("Downloading file to", path)
    conn = urlopen(url)
    if "Content-Length" not in conn.headers:
        raise ConnectionError("Content-Length not found")
    length = int(conn.headers["Content-Length"])
    print(f"File size: {length} ({round(length / 1048576, 2)}MB)")
    with open(path, "wb") as f:
        nl = length
        try:
            while True:
                blk = conn.read(4096)
                if not blk:
                    break
                nl -= len(blk)
                progress_bar(100 - int((nl / length) * 100), 4)
                f.write(blk)
        except (OSError, ConnectionError) as e:
            f.close()
            os.remove(path)
            raise e
        if nl:
            print("\nWarning: Incomplete file")
        else:
            print()


def gen_word(count: int, w: str) -> str:
    return "".join([w for _ in range(count)])


def progress_bar(present: int, resize: int = 1):
    size = 100 // resize
    if not present:
        out = f'\r[{gen_word(size, " ")}] {present}%'
    else:
        out = f'\r[{gen_word(present // resize, "#")}{gen_word(size - present // resize, " ")}] {present}%'
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
                try:
                    k, v = _.split("=", 1)
                except ValueError:
                    return None
                info[k] = v
            return bind_func(info)

    return __inner


def nt(rule: str, bind_func: Callable):
    def __inner(data: str):
        e = re.search(rule, data)
        if e:
            return bind_func(e)

    return __inner


def stop_process(manager):
    print("Stopping...")
    manager.close()
    if manager.is_alive():
        print("Stop fail. kill")
        manager.kill_process()
    print("Process Stopped")


class MiraiManager:
    def __init__(self, mcon_path: str, java_path: str = "java"):
        if not mcon_path:
            raise ValueError("mirai-console-wrapper path can't empty")
        self.__process = subprocess.Popen([java_path, "-jar", mcon_path, "--update", "keep"],
                                          stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def _readline(self) -> bytes:
        line = self.__process.stdout.readline().rstrip(b"\r\n")
        return line.lstrip(b"\x1b[0m ").rstrip(b"\x1b[39;49m")

    def command_execute(self, cm: str, *args):
        print(cm, args)
        self.__process.stdin.write(f"{cm} {' '.join(args)}\n".encode(encoding=encode_type, errors="ignore"))
        self.__process.stdin.flush()

    def listen(self, handlers=None):
        if not handlers:
            handlers = []
        while self.is_alive():
            data = self._readline().decode(encoding=encode_type, errors="ignore")
            if not data:
                print("Listener Stopped")
                sys.exit(0)
            print(data)
            for handle in handlers:
                if handle(data):
                    break

    def login(self, qq_num: str, password: str):
        self.command_execute("login", qq_num, password)

    def kill_process(self):
        self.__process.kill()

    def close(self, timeout=30):
        from signal import SIGTERM
        self.__process.send_signal(SIGTERM)  # Ctrl+C
        self.__process.wait(timeout)

    def is_alive(self) -> bool:
        if self.__process.poll() is None:
            return True
        else:
            return False
