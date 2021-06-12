import socket
import psutil as p
import yaml
import os
import pynvml
from _thread import *
import speedtest

# Read YAML file
with open("config.yaml", 'r') as stream:
    config_loaded = yaml.safe_load(stream)
    
# Global Fields
status = ''
onodes = []
onodes_connections = []
snodes = []
snode_connection = None
    
# Connecting to server's ip address
ClientMultiSocket = socket.socket()
host = config_loaded["server"]["ip"]
port = config_loaded["server"]["port"]
o_nodes_count = config_loaded["kazaa"]["o_node_per"]

username = input("Input your username: ")
print('Waiting for connection response')
try:
    ClientMultiSocket.connect((host, port))
except socket.error as e:
    print(str(e))

def memory():
    mem = p.virtual_memory()
    return (mem.total, mem.available)

def cpu():
    return (100-p.cpu_percent(), p.cpu_count(logical=True))

def gpu_memory():
    try:
        pynvml.nvmlInit()
        # 1 here is the GPU id
        handle = pynvml.nvmlDeviceGetHandleByIndex(1)
        meminfo = pynvml.nvmlDeviceGetMemoryInfo(handle)
        return meminfo.free
    except:
        return 0

def download_speed():
    st = speedtest.Speedtest()
    return st.download()/8
   
def multi_threaded_client(connection, id):
    print(str(id) + " inside")
        
# first check response received i.e "Server is working"
res = ClientMultiSocket.recv(1024).decode('utf-8')
print(res)

# sending system info
messages_to_send = 5
ClientMultiSocket.send(str.encode("rcv:"+str(messages_to_send)))

# download speed in bytes
ClientMultiSocket.send(str.encode(str(download_speed())))
# available GPU ram in bytes
ClientMultiSocket.send(str.encode(str(gpu_memory())))
# available ram in bytes
ClientMultiSocket.send(str.encode(str(memory()[1])))
# cpu free in percentage
ClientMultiSocket.send(str.encode(str(cpu()[0])))
# cpu cores in count
ClientMultiSocket.send(str.encode(str(cpu()[1])))

# receive acknowledge
print("\n" + "/"*40 + " waiting for ack " + "/"*40)
res = ClientMultiSocket.recv(1024).decode('utf-8')
print(res)
print("/"*90 + "\n")
    
# receive status in kazaa architecture
status = ClientMultiSocket.recv(1024).decode('utf-8')[len("status:"):]
print("\n" + "/"*40 + " waiting for ack " + "/"*40)
print("You are appointed as " + ("Super node." if status=="s" else "Ordinary node."))
print("/"*90 + "\n")

if status == "s":
    onodesSocket = socket.socket()
    host = socket.gethostname()
    oport = port + 1
    while(True):
        try:
            onodesSocket.bind((host, oport))
            print("Socket for listening to", o_nodes_count,"ordinary nodes is listening at "+host+":"+str(onodesSocket.getsockname()[1]))
            break
        except:
            oport += 1
    
    ClientMultiSocket.send(str.encode(str(host+":"+str(onodesSocket.getsockname()[1]))))
    onodesSocket.listen(o_nodes_count)
    print('Supernode is listening for', o_nodes_count, 'ordinary nodes..\n')
    
    id = 0
    while(id != o_nodes_count):
        Client, address = onodesSocket.accept()
        start_new_thread(multi_threaded_client, (Client, id))
        print('Thread Number: ' + str(id) + " - " + 'Connected to ordinary node: ' + address[0] + ':' + str(address[1]))
        id += 1
        onodes_connections.append((address[0], address[1], Client))
elif status == "o":
    ip_port = ClientMultiSocket.recv(1024).decode('utf-8').split(":")
    snodes.append((ip_port[0], int(ip_port[1])))
    
    for ip,port in snodes:
        print("Snode of my region is present at "+ip+":"+str(port))
    
    # starting connections with onodes:
    i = 0
    for ip,port in snodes:
        try:
            snode_connection = socket.socket()
            snode_connection.connect((ip, port))
            print("Connected to the supernode.\n")
        except socket.error as e:
            print(str(e))
        i += 1

# series of many to one communication between server and client
while True:
    messages_to_send = input('Write number of messages you want to send >>>> ')
    # send_socket_str(ClientMultiSocket, "rcv:"+messages_to_send)
    ClientMultiSocket.send(str.encode("rcv:"+messages_to_send))
    for i in range(int(messages_to_send)):
        Input = input('>>>> ')
        # send_socket_str(ClientMultiSocket, Input)
        ClientMultiSocket.send(str.encode(Input))
    if messages_to_send == "0":
        break
    # res = rcv_socket_str(ClientMultiSocket)
    res = ClientMultiSocket.recv(1024).decode('utf-8')
    print(res)

ClientMultiSocket.close()