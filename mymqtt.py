import paho.mqtt.client as mqtt
import os
import json
import time
import re

# pip install pywin32
import win32gui
import win32con
import subprocess

# 默认参数
DIR = os.path.dirname(os.path.realpath(__file__))
FILE = os.path.join(DIR, "config.json")
LOG_FILE = os.path.join(DIR, "log.txt")
HOST = "192.168.1.2"
PORT = 1883
PCNAME = "legionpc"
USER = ""
PASS = ""
COUNTDOWN = 20
DELAYSECONDS = 10
MQTT_TOPIC_STATE = f"{PCNAME}/state"
MQTT_TOPIC_SET = f"{PCNAME}/set"
global CLIENT


# 初始化或读取config.json
def init_mqtt_config():
    global COUNTDOWN, HOST, PORT, PCNAME, USER, PASS, FILE, DELAYSECONDS
    if os.path.exists(FILE):
        with open(FILE, "r", encoding="utf-8") as fp:
            data = json.load(fp)
            COUNTDOWN = data.get("countdown", COUNTDOWN)
            HOST = str(data.get("host", HOST))
            PORT = data.get("port", PORT)
            PCNAME = str(data.get("pcname", PCNAME))
            USER = str(data.get("user", USER))
            PASS = str(data.get("pass", PASS))
            DELAYSECONDS = data.get("delayseconds", DELAYSECONDS)
    else:
        params = {
            "countdown": COUNTDOWN,
            "host": HOST,
            "port": PORT,
            "pcname": PCNAME,
            "user": "",
            "pass": "",
            "delayseconds": DELAYSECONDS,
        }
        data = json.dumps(params, indent=1)
        with open(FILE, "w", encoding="utf-8", newline="\n") as fp:
            fp.write(data)


# 创建 MQTT 客户端
def mqtt_client():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, PCNAME)
    if USER != "" and PASS != "":
        client.username_pw_set(USER, PASS)
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    client.will_set(topic=MQTT_TOPIC_STATE, payload="off", qos=1, retain=True)
    # client.loop_forever()
    client.connect(HOST, PORT, 30)
    client.loop_start()
    return client


def send_status(client, status):
    client.publish(topic=MQTT_TOPIC_STATE, payload=status, qos=1)


def on_connect(client, userdata, flags, reason_code, properties):
    send_status(client, "on")
    client.subscribe(topic=MQTT_TOPIC_SET, qos=1)


def on_disconnect(client, userdata, flags, reason_code, properties):
    send_status(client, "off")


def on_message(client, userdata, msg):
    message = msg.payload.decode()
    if message == "off":
        cmd = f"shutdown -s -t {COUNTDOWN}"
        os.system(cmd)
        send_status(client, "off")
    elif message == "on":
        os.system("shutdown -a")
        send_status(client, "on")


# 启动时检查网络重试次数，最多检查4次
def retry_on_start(max_retries, ip_start):

    # 用于检测网络是否通顺
    def checkip(ip_start):
        result = subprocess.run(["ipconfig"], capture_output=True, text=True)
        ipv4_lines = result.stdout.splitlines()

        def find_matching_ipv4(line):
            match = re.search(r"IPv4 地址[^\d]+(\d+\.\d+\.\d+\.\d+)", line)
            return match.group(1) if match else None

        for line in ipv4_lines:
            ipv4 = find_matching_ipv4(line)
            if ipv4 and ipv4.startswith(ip_start):
                return True
        return False

    for i in range(max_retries):
        result = checkip(ip_start)
        if result:
            return True
        else:
            time.sleep(DELAYSECONDS)
    return False


def log_info(msg):
    format_str = f"【{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}】\t{msg}"
    with open(LOG_FILE, "a") as f:
        f.write(format_str + "\n")


def wndproc(hwnd, msg, wparam, lparam):
    # 关机时捕获到消息后执行的程序：17 是响应 WM_QUERYENDSESSION；22 是响应 WM_ENDSESSION
    log_info(f"关机时捕获到消息。消息类型：{str(msg)}，wparam：{str(wparam)}，lparam：{str(lparam)}")
    send_status(CLIENT, "off")
    time.sleep(10)  # 延迟一段时间以完成操作
    return True


def catch_shutdown_signal():
    log_info("****** 开始监听系统事件（关机、注销等） ******")

    hinst = win32gui.GetModuleHandle(None)
    wndclass = win32gui.WNDCLASS()
    wndclass.hInstance = hinst
    wndclass.lpszClassName = "testWindowClass"
    messageMap = {
        win32con.WM_QUERYENDSESSION: wndproc,
        win32con.WM_ENDSESSION: wndproc,
    }
    wndclass.lpfnWndProc = messageMap

    try:
        myWindowClass = win32gui.RegisterClass(wndclass)
        hwnd = win32gui.CreateWindowEx(
            win32con.WS_EX_LEFT,
            myWindowClass,
            "TestWindow",
            0,
            0,
            0,
            win32con.CW_USEDEFAULT,
            win32con.CW_USEDEFAULT,
            0,
            0,
            hinst,
            None,
        )
    except Exception as e:
        log_info(str(e))

    if hwnd is None:
        log_info("窗口创建失败")
    else:
        log_info("窗口句柄：" + str(hwnd))

    while True:
        win32gui.PumpWaitingMessages()
        time.sleep(1)


def runmqtt():
    init_mqtt_config()

    ip_start = "192.168.1"

    max_retries = 4
    if retry_on_start(max_retries, ip_start):
        CLIENT = mqtt_client()
        catch_shutdown_signal()
    else:
        log_info("网络连接失败，请检查网络设置和ip_start参数")
