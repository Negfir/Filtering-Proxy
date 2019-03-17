import socket, sys
from _thread import *
import base64

portNum= 5050;

max_con=5
buffer_size=8000

#data=0


def recieve():
    try:
        ser = '127.0.0.1'
        received = ""
        serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  ############
        serverSocket.bind((ser, portNum))
        serverSocket.listen(max_con)

        print("[*] Initializing Sockets... Done")
        print("[*] Sockets Binded Successfully...")
        print("[*] Server Started Successfully [ %d ]\n" % (portNum))
    except Exception as e:
        print ("error",e)
        sys.exit(2)

    while 1:
        try:
            conn, addr =serverSocket.accept()
            data= conn.recv(buffer_size)
            start_new_thread(conn_stab,(conn,data,addr))
        except KeyboardInterrupt:
            serverSocket.close()
            print("\n[*] Proxy Server Shutting Down..")
            sys.exit(1)
    serverSocket.close()

def conn_stab(conn, data, addr):
    try:
        #print(data)
        try:
            data = data.decode("ascii")
        except AttributeError:
            pass
        first_line = data.split('\n')[0]
        if first_line.strip():
            url= first_line.split(' ')[1]
            http_pos = url.find("://")

            if(http_pos==-1):
                temp=url
            else:
                temp =url[(http_pos+3):]
            port_pos=temp.find(":")
            webserver_pos=temp.find("/")
            if webserver_pos==-1:
                webserver_pos=len(temp)
            webserver=""
            port=-1
            if (port_pos==-1 or webserver_pos < port_pos):
                port =80
                webserver=temp[:webserver_pos]
            else:
                port = int((temp[(port_pos+1):])[:webserver_pos-port_pos-1])
                webserver=temp[:port_pos]

            #print(webserver, port, conn, addr, data)



            proxy(webserver,port,conn,addr,data)


    except Exception as e:
        print(e)
        pass

def proxy(webserver, port, conn,addr, data):
    try:
        # for x in data:
        #     print("\n", x)

        print(data)
        serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  ############
        serverSocket.connect((webserver, port))
        try:
            data = data.encode("ascii")
        except AttributeError:
            pass
        serverSocket.send(data)

        while 1:
            reply= serverSocket.recv(buffer_size)

            if(len(reply)>0):
                conn.send(reply)

                dar=float(len(reply))
                dar=float(dar / 1024)
                dar ="%.3s" %(str(dar))
                dar="%s KB" % (dar)
                print("[*] Request Done: %s => %s <=" % (str(addr[0]),str(dar)))
            else:
                break
        serverSocket.close()
        conn.close()
    except socket.error as e:
        serverSocket.close()
        conn.close()
        sys.exit(1)

recieve()