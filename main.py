import os
import getpass
import webbrowser
from threading import Thread
from helpers import MiraiManager, get_java_path, qt, nt, check_update, get_java, fuzzy_get


def open_in_browser(info):
    if webbrowser.open(info["url"]):
        print("请在浏览器中继续操作")
    else:
        print(f"请手动打开此链接：{info['url']}")


def on_error(info):
    # print(info)
    pass


def login_success(reg):
    # print(reg)
    pass


def command_transparent(manager: MiraiManager):
    while True:
        cmd = input().split(" ")
        manager.command_execute(cmd[0], *cmd[1:])


if __name__ == '__main__':
    if not get_java_path():
        print("Java not exist, installing...")
        if not get_java():
            print("install failed, exiting...")
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
                print("password save to .passwd")
                break
            else:
                print("Please input your qq_num and password.")
    m.login(*(open(".passwd", "r", encoding="utf-8", errors="ignore").read().split(" ", 1)))
    try:
        Thread(target=command_transparent, args=[m], name="InputListener").start()
        m.listen(
            [
                qt("Error", on_error),
                qt("UnsafeLogin", open_in_browser),
                nt(r"(\d*) login successes", login_success)
            ]
        )
    except KeyboardInterrupt:
        print("Exiting...")
        try:
            m.close()
            if m.is_alive():
                m.kill_process()
        except KeyboardInterrupt:
            print("Force exit")
            m.kill_process()
