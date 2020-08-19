import os
import sys
import getpass
import webbrowser
from threading import Thread
from helpers import MiraiManager, get_java_path, qt, nt, check_update, \
    get_java, fuzzy_get, stop_process, fprint


def open_in_browser(info):
    if webbrowser.open(info["url"]):
        fprint("请在浏览器中继续操作")
    else:
        fprint(f"请手动打开此链接：{info['url']}")


def on_error(info):
    pass
    # if info["title"] == "登录失败":
    #    os.remove(".passwd")


def login_success(reg):
    # print(reg)
    pass


def command_transparent(manager: MiraiManager):
    while True:
        try:
            cmd = input().split(" ")
        except EOFError:  # Ctrl+Z on Windows
            cmd = ["stop"]
        if cmd[0] == "stop":
            stop_process(manager)
            sys.exit(0)
        else:
            manager.command_execute(cmd[0], *cmd[1:])


if __name__ == '__main__':
    if not get_java_path():
        fprint("Java not exist, installing...")
        if not get_java():
            fprint("install failed, exiting...")
            os.remove(path=fuzzy_get("jdk_bin"))
            exit(1)
    check_update()
    m = MiraiManager(
        fuzzy_get("mirai-console-wrapper-(.*).jar"),
        get_java_path()
    )
    if not os.path.isfile(".passwd"):
        while True:
            qq_num, password = input("QQ_Num: "), getpass.getpass("Password: ")
            if qq_num and password:
                with open(".passwd", "w") as f:
                    f.write(" ".join((qq_num, password)))
                fprint("password save to .passwd")
                break
            else:
                fprint("Please input your qq_num and password.")
    m.login(*(open(".passwd", "r", encoding="utf-8", errors="ignore").read().split(" ", 1)))
    try:
        t = Thread(target=command_transparent, args=[m], name="InputListener", daemon=True)
        t.start()
        m.listen(
            [
                qt("Error", on_error),
                qt("UnsafeLogin", open_in_browser),
                nt(r"(\d*) login successes", login_success)
            ]
        )
    except KeyboardInterrupt:
        fprint("Exiting...")
        stop_process(m)
