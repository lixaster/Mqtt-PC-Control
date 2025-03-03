import sys
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon, QWidget
from PySide6.QtGui import QIcon, QAction
import multiprocessing
import subprocess
from mymqtt import runmqtt, log_info
import os

# 文件目录
DIR = os.path.dirname(os.path.realpath(__file__))
TRAY_ICON = os.path.join(DIR, "ui_icon.png")
ENABLED_ICON = os.path.join(DIR, "enabled_icon.png")
LOG_FILE = os.path.join(DIR, "log.txt")


class MyApplication(QApplication):
    def __init__(self, sys_argv):
        super().__init__(sys_argv)

        self.tray_icon = QSystemTrayIcon(QIcon(TRAY_ICON), self)
        self.tray_icon.setToolTip("MQTT远程开关机")
        self.tray_icon.show()

        self.create_context_menu()

        self.mqtt_process = None

        # 默认状态为启用
        self.enabled = False
        self.update_status()
        self.toggle_mqtt()

    def create_context_menu(self):
        self.tray_menu = QMenu()

        self.enable_action = QAction("启用", self)
        self.enable_action.triggered.connect(self.toggle_mqtt)
        self.tray_menu.addAction(self.enable_action)

        self.log_action = QAction("日志", self)
        self.log_action.triggered.connect(self.show_log)
        self.tray_menu.addAction(self.log_action)

        about_action = QAction("关于", self)
        about_action.triggered.connect(self.about)
        self.tray_menu.addAction(about_action)

        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.exit_app)
        self.tray_menu.addAction(exit_action)

        self.tray_icon.setContextMenu(self.tray_menu)

    def toggle_mqtt(self):
        if not self.enabled:
            self.mqtt_process = multiprocessing.Process(target=runmqtt)
            self.mqtt_process.start()
            self.enabled = True
            self.update_status()
            log_info("MQTT功能启用成功")
        else:
            if self.mqtt_process and self.mqtt_process.is_alive():
                self.mqtt_process.terminate()
                self.mqtt_process.join()
                self.enabled = False
                self.update_status()
                log_info("MQTT功能已禁用")
            else:
                log_info("MQTT子进程未在运行")

    def show_log(self):
        subprocess.Popen(["notepad", LOG_FILE])

    def about(self):
        dummy_widget = QWidget()  # 创建一个空的QWidget对象
        QMessageBox.about(
            dummy_widget, "关于", "作者：lixaster\n版本：1.0.0\n日期：2024-04-01"
        )

    def exit_app(self):
        if self.enabled:
            self.mqtt_process.terminate()
            self.mqtt_process.join()
        self.tray_icon.hide()
        log_info("-------程序退出-------")
        sys.exit()

    def update_status(self):
        if self.enabled:
            self.enable_action.setIcon(QIcon(ENABLED_ICON))  # 替换为你的启用图标
        else:
            self.enable_action.setIcon(QIcon())  # 清除图标


if __name__ == "__main__":
    multiprocessing.freeze_support()
    log_info("-------程序启动-------")
    app = MyApplication(sys.argv)
    sys.exit(app.exec())
