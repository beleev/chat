#! /usr/bin/env python
# -*- encoding: utf-8 -*-
import json
import time
import signal
import ctypes
from utils import chatbot

run_path = "/home/work"

class SceneManager(object):

    def __init__(self, chat_server, plugin_port, username, db_conf_path):
        self.chat_server = chat_server
        self.plugin_port = plugin_port
        self.bot_list = {}
        self.runFlag = False
        # 默认时间 20 min
        self.time_period = 20 * 60

        self.username = username
        self.userId = None
        self.db_conf = db_conf_path
        self.script = None

    def _next_port(self):
        ret = self.plugin_port
        self.plugin_port += 1
        return str(ret)

    def _start_all_bot(self):
        for k, v in self.bot_list.items():
            v.start()
        runOK = False
        while not runOK:
            for k, v in self.bot_list.items():
                if not v.runFlag:
                    time.sleep(1)
                    break
            runOK = True

    def _stop_all_bot(self):
        for k, v in self.bot_list.items():
            v.exit()
        for k, v in self.bot_list.items():
            v.join()

    def _add_bot(self, auth):
        token = auth + ":" + auth
        plugin_server = "0.0.0.0:" + self._next_port()
        self.bot_list[auth] = chatbot.ChatBot(self.chat_server, plugin_server, token)

    def _sendMsg(self, auth, topic, text):
        # msg = self.bot_list[auth].publish(topic, text)
        self.bot_list[auth].send_message(topic, text)

    def init_scene(self, schema):
        str_schema = json.dumps(schema)
        db_init = ctypes.CDLL(run_path + "lib_db_init.so").initScene
        db_init.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
        db_init.restype = ctypes.c_char_p
        db_ret = db_init(bytes(self.username, encoding = "utf8"),
                         bytes(str_schema, encoding = "utf8"), bytes(self.db_conf, encoding = "utf8"))
        exec_scene = json.loads(db_ret)

        for message in exec_scene["messages"]:
            if not self.bot_list.get(message["from"]):
                self._add_bot(message["from"])

        for k, v in exec_scene["roles"].items():
            if self.username == k:
                self.userId = v

        self.script = exec_scene["messages"]

    def run(self):
        self.runFlag = True
        script_arred = sorted(self.script, key=lambda x:int(x["time"]))

        self._start_all_bot()
        time_count = 0
        index = 0
        while time_count < self.time_period:
            while index < len(script_arred) \
                    and time_count == int(script_arred[index]["time"]):
                msg = script_arred[index]
                self._sendMsg(msg["from"], msg["to"], msg["text"])
                index += 1
            if not self.runFlag:
                print("Manager exit...")
                break
            time.sleep(1)
            time_count += 1
        self._stop_all_bot()


    def stop(self):
        print("Terminated scene by trigger.")
        self.runFlag = False


if __name__ == "__main__":
    print("test start")
    sm = SceneManager("127.0.0.1:6061", 40050, "小虾", "tinode.conf.db")
    with open("demo_template.json") as f:
        schema = json.load(f)
        sm.init_scene(schema)
        sm.run()


