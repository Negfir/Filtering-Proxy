#!/usr/bin/env python3

import sys

from argparse import ArgumentParser
from socket import TCP_NODELAY
from time import time
from traceback import print_exc
import asyncio
import logging
import random
import functools
import re
import PyQt5
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5 import QtGui
import urllib.request
from PyQt5.QtGui import QIcon

work =[]
lifeStyle=[]
sport=[]
education =[]
full_list=[]
full_list.append(work)
full_list.append(lifeStyle)
full_list.append(sport)
full_list.append(education)
REGEX_HOST           = re.compile(r'(.+?):([0-9]{1,5})')
REGEX_CONTENT_LENGTH = re.compile(r'\r\nContent-Length: ([0-9]+)\r\n', re.IGNORECASE)
REGEX_CONNECTION     = re.compile(r'\r\nConnection: (.+)\r\n', re.IGNORECASE)

clients = {}

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] {%(levelname)s} %(message)s')
logging.getLogger('asyncio').setLevel(logging.CRITICAL)
logger = logging.getLogger('warp')
verbose = 0


def accept_client(client_reader, client_writer, *, loop=None):
    ident = hex(id(client_reader))[-6:]
    task = asyncio.async(process_warp(client_reader, client_writer, loop=loop), loop=loop)
    clients[task] = (client_reader, client_writer)
    started_time = time()

    def client_done(task):
        del clients[task]
        client_writer.close()
        logger.debug('[%s] Connection closed (took %.5f seconds)' % (ident, time() - started_time))

    logger.debug('[%s] Connection started' % ident)
    task.add_done_callback(client_done)


@asyncio.coroutine
def process_warp(client_reader, client_writer, *, loop=None):
    ident = str(hex(id(client_reader)))[-6:]

    header = ''
    payload = b''
    try:
        RECV_MAX_RETRY = 3
        recvRetry = 0
        while True:
            line = yield from client_reader.readline()
            if not line:
                if len(header) == 0 and recvRetry < RECV_MAX_RETRY:
                    # handle the case when the client make connection but sending data is delayed for some reasons
                    recvRetry += 1
                    yield from asyncio.sleep(0.2, loop=loop)
                    continue
                else:
                    break
            if line == b'\r\n':
                break
            if line != b'':
                header += line.decode()

        m = REGEX_CONTENT_LENGTH.search(header)
        if m:
            cl = int(m.group(1))
            while (len(payload) < cl):
                payload += yield from client_reader.read(1024)
    except:
        print_exc()

    if len(header) == 0:
        logger.debug('[%s] !!! Task reject (empty request)' % ident)
        return

    req = header.split('\r\n')[:-1]
    if len(req) < 4:
        logger.debug('[%s] !!! Task reject (invalid request)' % ident)
        return
    head = req[0].split(' ')
    if head[0] == 'CONNECT': # https proxy
        try:
            searchfile2 = open("link.txt", "r")
            for list in full_list:
                for s in list:
                    if str(head[1]).find(s) == -1:
                        print("No here!  ",str(head[1]),s)

                    else:
                        print("Found string.")
                        print("FILTER", s)
                        return

                # #print(head[1])
                # if str(head[1]).find(str(line)) == -1:
                #     print("No here!  ",str(head[1]),str(line))
                #
                # else:
                #     print("Found string.")
                #     print("FILTER", line)
                #     return

            logger.info('%sBYPASSING <%s %s> (SSL connection)' %
                ('[%s] ' % ident if verbose >= 1 else '', head[0], head[1]))
            m = REGEX_HOST.search(head[1])
            host = m.group(1)
            port = int(m.group(2))
            req_reader, req_writer = yield from asyncio.open_connection(host, port, ssl=False, loop=loop)
            client_writer.write(b'HTTP/1.1 200 Connection established\r\n\r\n')
            @asyncio.coroutine
            def relay_stream(reader, writer):
                try:
                    while True:
                        line = yield from reader.read(1024)
                        if len(line) == 0:
                            break
                        writer.write(line)
                except:
                    print_exc()
            tasks = [
                asyncio.async(relay_stream(client_reader, req_writer), loop=loop),
                asyncio.async(relay_stream(req_reader, client_writer), loop=loop),
            ]
            yield from asyncio.wait(tasks, loop=loop)
        except:
            print_exc()
        finally:
            return
    phost = False
    sreq = []
    sreqHeaderEndIndex = 0
    for line in req[1:]:
        headerNameAndValue = line.split(': ', 1)
        if len(headerNameAndValue) == 2:
            headerName, headerValue = headerNameAndValue
        else:
            headerName, headerValue = headerNameAndValue[0], None

        if headerName.lower() == "host":
            phost = headerValue
        elif headerName.lower() == "connection":
            if headerValue.lower() in ('keep-alive', 'persist'):
                # current version of this program does not support the HTTP keep-alive feature
                sreq.append("Connection: close")
            else:
                sreq.append(line)
        elif headerName.lower() != 'proxy-connection':
            sreq.append(line)
            if len(line) == 0 and sreqHeaderEndIndex == 0:
                sreqHeaderEndIndex = len(sreq) - 1
    if sreqHeaderEndIndex == 0:
        sreqHeaderEndIndex = len(sreq)

    m = REGEX_CONNECTION.search(header)
    if not m:
        sreq.insert(sreqHeaderEndIndex, "Connection: close")

    if not phost:
        phost = '127.0.0.1'
    path = head[1][len(phost)+7:]
    searchfile = open("link.txt", "r")
    for list in full_list:
        for s in list:
            if str(head[1]).find(s) == -1:
                print("No here!  ", str(head[1]), s)

            else:
                print("Found string.")
                print("FILTER", s)
                return
    searchfile.close()
    # if (head[1]=="http://airnow.tehran.ir/"):
    #     head[1]="https://ceit.aut.ac.ir/~9431018/filter.html"
    #     return
    logger.info('%sWARPING <%s %s>' % ('[%s] ' % ident if verbose >= 1 else '', head[0], head[1]))

    new_head = ' '.join([head[0], path, head[2]])

    m = REGEX_HOST.search(phost)
    if m:
        host = m.group(1)
        port = int(m.group(2))
    else:
        host = phost
        port = 80

    try:
        req_reader, req_writer = yield from asyncio.open_connection(host, port, flags=TCP_NODELAY, loop=loop)
        req_writer.write(('%s\r\n' % new_head).encode())
        yield from req_writer.drain()
        yield from asyncio.sleep(0.2, loop=loop)

        def generate_dummyheaders():
            def generate_rndstrs(strings, length):
                return ''.join(random.choice(strings) for _ in range(length))
            import string
            return ['X-%s: %s\r\n' % (generate_rndstrs(string.ascii_uppercase, 16),
                generate_rndstrs(string.ascii_letters + string.digits, 128)) for _ in range(32)]

        req_writer.writelines(list(map(lambda x: x.encode(), generate_dummyheaders())))
        yield from req_writer.drain()

        req_writer.write(b'Host: ')
        yield from req_writer.drain()
        def feed_phost(phost):
            i = 1
            while phost:
                yield random.randrange(2, 4), phost[:i]
                phost = phost[i:]
                i = random.randrange(2, 5)
        for delay, c in feed_phost(phost):
            yield from asyncio.sleep(delay / 10.0, loop=loop)
            req_writer.write(c.encode())
            yield from req_writer.drain()
        req_writer.write(b'\r\n')
        req_writer.writelines(list(map(lambda x: (x + '\r\n').encode(), sreq)))
        req_writer.write(b'\r\n')
        if payload != b'':
            req_writer.write(payload)
            req_writer.write(b'\r\n')
        yield from req_writer.drain()

        try:
            while True:
                buf = yield from req_reader.read(1024)
                if len(buf) == 0:
                    break
                client_writer.write(buf)
        except:
            print_exc()

    except:
        print_exc()

    client_writer.close()


@asyncio.coroutine
def start_warp_server(host, port, *, loop = None):
    try:
        accept = functools.partial(accept_client, loop=loop)
        server = yield from asyncio.start_server(accept, host=host, port=port, loop=loop)
    except OSError as ex:
        logger.critical('!!! Failed to bind server at [%s:%d]: %s' % (host, port, ex.args[1]))
        raise
    else:
        logger.info('Server bound at [%s:%d].' % (host, port))
        return server


def main():
    """CLI frontend function.  It takes command line options e.g. host,
    port and provides `--help` message.
    """
    parser = ArgumentParser(description='Simple HTTP transparent proxy')
    parser.add_argument('-H', '--host', default='127.0.0.1',
                      help='Host to listen [default: %(default)s]')
    parser.add_argument('-p', '--port', type=int, default=8800,
                      help='Port to listen [default: %(default)d]')
    parser.add_argument('-v', '--verbose', action='count', default=0,
                      help='Print verbose')
    args = parser.parse_args()
    if not (1 <= args.port <= 65535):
        parser.error('port must be 1-65535')
    if args.verbose >= 3:
        parser.error('verbose level must be 1-2')
    if args.verbose >= 1:
        logger.setLevel(logging.DEBUG)
    if args.verbose >= 2:
        logging.getLogger('warp').setLevel(logging.DEBUG)
        logging.getLogger('asyncio').setLevel(logging.DEBUG)
    global verbose
    verbose = args.verbose
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(start_warp_server(args.host, args.port))
        loop.run_forever()
    except OSError:
        pass
    except KeyboardInterrupt:
        print('bye')
    finally:
        loop.close()


# import sys
from PyQt5.QtCore import *
from PyQt5.QtGui import *
items = ("Work", "Sport", "Lifestyle", "Education")
item=''

class inputdialogdemo(QWidget):
    def __init__(self, parent=None):

        super(inputdialogdemo, self).__init__(parent)


        layout = QFormLayout()
        self.btn = QPushButton("Choose your Group")
        self.btn.clicked.connect(self.getItem)

        self.le = QLineEdit()
        layout.addRow(self.btn, self.le)
        self.btn1 = QPushButton("Site Address")
        self.btn1.clicked.connect(self.gettext)

        self.le1 = QLineEdit()
        layout.addRow(self.btn1, self.le1)
        # self.btn2 = QPushButton("New Group")
        # self.btn2.clicked.connect(self.getint)

        self.le2 = QLineEdit()
        #layout.addRow(self.btn2, self.le2)
        self.setLayout(layout)
        self.setWindowTitle("Add sites")

    def getItem(self):

        global item
        item, ok = QInputDialog.getItem(self, "select input dialog",
                                        "list of languages", items, 0, False)

        if ok and item:
            self.le.setText(item)

    def gettext(self):
        text, ok = QInputDialog.getText(self, 'Site Input Dialog', 'Enter your site:')

        if ok:
            print(item)
            if (item == "Work"):
                work.append(str(text))
                print("added to work")
            if (item == "Sport"):
                sport.append(str(text))
                print("added to Sport")
            if (item == "Lifestyle"):
                lifeStyle.append(str(text))
                print("added to Lifestyle")
            if (item == "Education"):
                education.append(str(text))
                print("added to Education")
            self.le1.setText(str(text))
            # searchfile = open("link.txt", "a")
            # searchfile.write(str(text))
            # searchfile.write("\n")
            # searchfile.close()



    # def getint(self):
    #     text, ok = QInputDialog.getText(self, 'Group input', 'Enter your Group:')
    #
    #     #if ok:
    #         #items.append(str(text))
    #
    # def on_button_clicked(self):
    #     print('You clicked the button!')
    #     #main()


def main1():
    app = QApplication(sys.argv)
    ex = inputdialogdemo()
    ex.show()

    app.exec_()




if __name__ == '__main__':
    main1()
    main()
    # items = ("Work", "Sport", "Lifestyle", "Education",)
    #
    # item, ok = QInputDialog.getItem(self,"select input dialog",
    #                                 "list of languages", items, 0, False)
    #
    # if ok and item:
    #     print("click")
    #
    # app = QApplication([])
    # button = QPushButton('Click')
    #
    # def on_button_clicked():
    #     #alert.setText('You clicked the button!')
    #     main()
    #     # alert = QMessageBox()
    #     # alert.setText('You clicked the button!')
    #     # alert.exec_()
    #
    # button.clicked.connect(on_button_clicked)
    # button.show()
    # app.exec_()



    #main()