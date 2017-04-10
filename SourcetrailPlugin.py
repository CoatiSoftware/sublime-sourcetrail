import sublime
import sublime_plugin
import threading
import socket
import os.path
import encodings.idna

try:						# use this for Sublime Text 2
    import SocketServer
except ImportError:			# use this for Sublime Text 3
    import socketserver as SocketServer

MESSAGE_SPLIT_STRING = ">>"


# Handling SourceTrail to Sublime communication

def setCursorPosition(filePath, row, col):
    if (os.path.exists(filePath)):
        sublime.active_window().open_file(filePath + ":" + str(row) +
                                          ":" + str(col), sublime.ENCODED_POSITION)
    else:
        sublime.error_message(
            "SourceTrail is trying to jump to a file that does not exist: " + filePath)


def sendPing():
    settings = sublime.load_settings('SourceTrailPlugin.sublime-settings')
    host_ip = settings.get('host_ip')
    plugin_to_sourcetrail_port = settings.get('sublime_to_sourcetrail_port')

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host_ip, plugin_to_sourcetrail_port))
    message = "ping>>SublimeText<EOM>"
    s.send(message.encode())
    s.close()


# This class is instantiated once per connection to the server
class ConnectionHandler(SocketServer.BaseRequestHandler):

    def handle(self):
        data = self.request.recv(1024).strip()
        text = data.decode('utf-8')
        eom_index = text.find("<EOM>")
        if (not eom_index == 0):
            message_string = text[0:eom_index]
            message_fields = message_string.split(MESSAGE_SPLIT_STRING)
            if (message_fields[0] == "moveCursor"):
                sublime.set_timeout(lambda: setCursorPosition(
                    message_fields[1], int(message_fields[2]), int(message_fields[3]) + 1), 0)
            if (message_fields[0] == "ping"):
                sendPing()


class ServerThreadHandler(threading.Thread):

    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        threading.Thread.__init__(self)

    def run(self):
        server = SocketServer.TCPServer(
            (self.ip, self.port), ConnectionHandler)
        server.serve_forever()


class ServerStartupListener(sublime_plugin.EventListener):

    def __init__(self):
        self.running = False

    def on_activated(self, view):
        if (not self.running):
            self.running = True

            settings = sublime.load_settings('SourceTrailPlugin.sublime-settings')
            host_ip = settings.get('host_ip')
            sourcetrail_to_plugin_port = settings.get('sourcetrail_to_sublime_port')

            networkListener = ServerThreadHandler(
                host_ip, sourcetrail_to_plugin_port)
            networkListener.start()
            sendPing()


# Handling Sublime to SourceTrail communication

class SetActiveTokenCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        filePath = self.view.file_name()

        selectionPos = self.view.sel()[0].begin()
        (row, col) = self.view.rowcol(selectionPos)
        col += 1  # cols returned by rowcol() are 0-based.
        row += 1  # rows returned by rowcol() are 0-based.

        text = "setActiveToken" + MESSAGE_SPLIT_STRING + filePath + \
            MESSAGE_SPLIT_STRING + \
            str(row) + MESSAGE_SPLIT_STRING + str(col) + "<EOM>"
        data = text.encode()

        settings = sublime.load_settings('SourceTrailPlugin.sublime-settings')
        host_ip = settings.get('host_ip')
        plugin_to_sourcetrail_port = settings.get('sublime_to_sourcetrail_port')

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host_ip, plugin_to_sourcetrail_port))
        s.send(data)
        s.close()
