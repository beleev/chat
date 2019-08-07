"""Python implementation of a Tinode chatbot."""

# For compatibility between python 2 and 3
from __future__ import print_function

import base64
from concurrent import futures
import json
import os
import pkg_resources
import platform
try:
    import Queue as queue
except ImportError:
    import queue
import time

import grpc
import threading

# Import generated grpc modules
from tinode_grpc import pb
from tinode_grpc import pbx

APP_NAME = "Tino-chatbot"
APP_VERSION = "1.1.3"
LIB_VERSION = pkg_resources.get_distribution("tinode_grpc").version

# This is needed for gRPC ssl to work correctly.
os.environ["GRPC_SSL_CIPHER_SUITES"] = "HIGH+ECDSA"


# This is the class for the server-side gRPC endpoints
class Plugin(pbx.PluginServicer):

    def Account(self, acc_event, context):
        action = None
        if acc_event.action == pb.CREATE:
            action = "created"
            # TODO: subscribe to the new user.
        elif acc_event.action == pb.UPDATE:
            action = "updated"
        elif acc_event.action == pb.DELETE:
            action = "deleted"
        else:
            action = "unknown"
        print("Account", action, ":", acc_event.user_id, acc_event.public)
        return pb.Unused()


class ChatBot(threading.Thread):

    def __init__(self, chat_server, plugin_server, auth):
        threading.Thread.__init__(self)

        # User ID of the current user
        self.botUID = None
        # Dictionary wich contains lambdas to be executed when server response is received
        self.onCompletion = {}
        self.subscriptions = {}
        # Quotes from the fortune cookie file
        self.queue_out = queue.Queue()
        self.tid = 100

        self.chat_server = chat_server
        self.plugin_server = plugin_server
        self.auth = auth

        self.server = None
        self.client = None
        self.runFlag = False

    def next_id(self):
        self.tid += 1
        return str(self.tid)

    # Add bundle for future execution
    def add_future(self, tid, bundle):
        self.onCompletion[tid] = bundle

    # Resolve or reject the future
    def exec_future(self, tid, code, text, params):
        bundle = self.onCompletion.get(tid)
        if bundle != None:
            del self.onCompletion[tid]
            if code >= 200 and code < 400:
                arg = bundle.get('arg')
                bundle.get('action')(arg, params)
            else:
                print("Error:", code, text)

    # List of active subscriptions
    def add_subscription(self, topic):
        self.subscriptions[topic] = True

    def del_subscription(self, topic):
        self.subscriptions.pop(topic, None)

    def server_version(self, params):
        if params == None:
            return
        print("Server:", params['build'].decode('ascii'), params['ver'].decode('ascii'))


    def client_generate(self):
        while True:
            msg = self.queue_out.get()
            if msg == None:
                return
            # print("out:", msg)
            yield msg

    def client_post(self, msg):
        self.queue_out.put(msg)

    def client_reset(self):
        # Drain the queue
        try:
            while self.queue_out.get(False) != None:
                pass
        except queue.Empty:
            pass

    def hello(self):
        tid = self.next_id()
        self.add_future(tid, {
            'action': lambda unused, params: self.server_version(params),
        })
        return pb.ClientMsg(hi=pb.ClientHi(id=tid, user_agent=APP_NAME + "/" + APP_VERSION + " (" +
            platform.system() + "/" + platform.release() + "); gRPC-python/" + LIB_VERSION,
            ver=LIB_VERSION, lang="EN"))

    def login(self, cookie_file_name, scheme, secret):
        tid = self.next_id()
        self.add_future(tid, {
            'arg': cookie_file_name,
            'action': lambda fname, params: self.on_login(fname, params),
        })
        return pb.ClientMsg(login=pb.ClientLogin(id=tid, scheme=scheme, secret=secret))

    def subscribe(self, topic):
        tid = self.next_id()
        self.add_future(tid, {
            'arg': topic,
            'action': lambda topicName, unused: self.add_subscription(topicName),
        })
        return pb.ClientMsg(sub=pb.ClientSub(id=tid, topic=topic))

    def leave(self, topic):
        tid = self.next_id()
        self.add_future(tid, {
            'arg': topic,
            'action': lambda topicName, unused: self.del_subscription(topicName)
        })
        return pb.ClientMsg(leave=pb.ClientLeave(id=tid, topic=topic))

    def publish(self, topic, text):
        tid = self.next_id()
        return pb.ClientMsg(pub=pb.ClientPub(id=tid, topic=topic, no_echo=True,
            head={"auto": json.dumps(True).encode('utf-8')}, content=json.dumps(text).encode('utf-8')))

    def note_read(self, topic, seq):
        return pb.ClientMsg(note=pb.ClientNote(topic=topic, what=pb.READ, seq_id=seq))

    def send_message(self, to, text):
        self.client_post(self.subscribe(to))
        time.sleep(0.5)
        self.client_post(self.publish(to, text))

    def init_server(self, listen):
        # Launch plugin server: acception connection(s) from the Tinode server.
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=16))
        pbx.add_PluginServicer_to_server(Plugin(), server)
        server.add_insecure_port(listen)
        server.start()
        print("Plugin server running at '"+listen+"'")
        return server

    def init_client(self, addr, schema, secret, cookie_file_name):
        print("Connecting to server at", addr)

        channel = None
        channel = grpc.insecure_channel(addr)

        # Call the server
        stream = pbx.NodeStub(channel).MessageLoop(self.client_generate())

        # Session initialization sequence: {hi}, {login}, {sub topic='me'}
        self.client_post(self.hello())
        self.client_post(self.login(cookie_file_name, schema, secret))
        self.client_post(self.subscribe('me'))

        return stream

    def client_message_loop(self, stream):
        try:
            self.runFlag = True
            # Read server responses
            for msg in stream:
                # print("in:", msg)
                if msg.HasField("ctrl"):
                    # Run code on command completion
                    self.exec_future(msg.ctrl.id, msg.ctrl.code, msg.ctrl.text, msg.ctrl.params)

                elif msg.HasField("data"):
                    # print("message from:", msg.data.from_user_id)

                    # Protection against the bot talking to self from another session.
                    # 只回复非群组消息
                    if msg.data.from_user_id != self.botUID and msg.data.topic[0:3] != 'grp':
                        # Respond to message.
                        # Mark received message as read
                        self.client_post(self.note_read(msg.data.topic, msg.data.seq_id))
                        # Insert a small delay to prevent accidental DoS self-attack.
                        time.sleep(0.1)
                        # Respond with a witty quote
                        self.client_post(self.publish(msg.data.topic, "ok"))

                elif msg.HasField("pres"):
                    # print("presence:", msg.pres.topic, msg.pres.what)
                    # Wait for peers to appear online and subscribe to their topics
                    if msg.pres.topic == 'me':
                        if (msg.pres.what == pb.ServerPres.ON or msg.pres.what == pb.ServerPres.MSG) \
                                and self.subscriptions.get(msg.pres.src) == None:
                            self.client_post(self.subscribe(msg.pres.src))
                        elif msg.pres.what == pb.ServerPres.OFF and self.subscriptions.get(msg.pres.src) != None:
                            self.client_post(self.leave(msg.pres.src))

                else:
                    # Ignore everything else
                    pass
        except grpc._channel._Rendezvous as err:
            print("Disconnected:", err)

    def read_auth_cookie(self, cookie_file_name):
        """Read authentication token from a file"""
        cookie = open(cookie_file_name, 'r')
        params = json.load(cookie)
        cookie.close()
        schema = params.get("schema")
        secret = None
        if schema == None:
            return None, None
        if schema == 'token':
            secret = base64.b64decode(params.get('secret').encode('utf-8'))
        else:
            secret = params.get('secret').encode('utf-8')
        return schema, secret

    def on_login(self, cookie_file_name, params):
        """Save authentication token to file"""
        if params == None or cookie_file_name == None:
            return

        if 'user' in params:
            botUID = params['user'].decode("ascii")

        # Protobuf map 'params' is not a python object or dictionary. Convert it.
        nice = {'schema': 'token'}
        for key_in in params:
            if key_in == 'token':
                key_out = 'secret'
            else:
                key_out = key_in
            nice[key_out] = json.loads(params[key_in].decode('utf-8'))

        try:
            cookie = open(cookie_file_name, 'w')
            json.dump(nice, cookie)
            cookie.close()
        except Exception as err:
            print("Failed to save authentication cookie", err)

    def run(self):
        """Use username:password"""

        schema = 'basic'
        secret = self.auth.encode('utf-8')
        login_cookie = ".bot-cookie-" + self.auth
        print("Logging in with login:password", secret)

        # Start Plugin server
        self.server = self.init_server(self.plugin_server)
        # Initialize and launch client
        self.client = self.init_client(self.chat_server, schema, secret, login_cookie)

        # Run blocking message loop in a cycle to handle
        # server being down.
        while True:
            self.client_message_loop(self.client)
            if not self.runFlag:
                return
            time.sleep(3)
            self.client_reset()
            self.client = self.init_client(self.chat_server, schema, secret, login_cookie)

        # Close connections gracefully before exiting
        self.server.stop(None)
        self.client.cancel()

    def exit(self):
        print("Terminated Bot")
        self.server.stop(0)
        self.client.cancel()
        self.runFlag = False


if __name__ == '__main__':
    """Parse command-line arguments. Extract server host name, listen address, authentication scheme"""

    bot = ChatBot("127.0.0.1:6061", "0.0.0.0:40051", "alice:alice")
    bot.start()
    bot.join()
