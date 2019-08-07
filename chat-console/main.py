#! /usr/bin/env python
# -*- encoding: utf-8 -*-
import scene_manager
import threading

from flask import Flask
from flask import jsonify
from flask import request
from flask import abort
from flask import make_response
from flask import render_template

from utils import log

log.init_log('./log/bi')
app = Flask(__name__)
char_server = "http://127.0.0.1:6060"
bot_server = "127.0.0.1:6061"
scence = {}
port_allocated = 40050
run_path = "/home/work"
lock = threading.Lock()

@app.route("/")
def echo():
    """
    Echo Service
    """
    return render_template('index.html')


@app.route("/api/init", methods=['POST'])
def initChat():
    """
    """
    if not request.json:
        abort(404)
    ret = {}
    recv = request.json
    if len(recv["messages"]) == 0:
        ret["msg"] = "No info provided"
        return make_response(jsonify(ret), 200)

    with lock:
        global port_allocated
        sm = scene_manager.SceneManager(bot_server, port_allocated, "you", run_path + "tinode.conf.db")
        sm.init_scene(recv)
        scence[sm.userId] = sm
        port_allocated += len(sm.bot_list)

        ret["chat"] = char_server
        ret["user"] = sm.userId
        ret["msg"] = "ok"

    return make_response(jsonify(ret), 200)

@app.route("/api/start", methods=['POST'])
def startChat():
    """
    """
    if not request.json:
        abort(404)
    p = threading.Thread(target=scence[request.json["id"]].run)
    p.start()
    return make_response(jsonify({'msg': 'ok'}), 200)


@app.route("/api/stop", methods=['POST'])
def stopChat():
    """
    """
    if not request.json:
        abort(404)
    scence[request.json["id"]].stop()
    return make_response(jsonify({'msg': 'ok'}), 200)


@app.errorhandler(404)
def not_found(error):
    """
    Error handler
    """
    return make_response(jsonify({'error': 'Not found'}), 404)


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=8080)
