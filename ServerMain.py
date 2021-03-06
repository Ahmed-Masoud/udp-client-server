from server import Server
from Packet import Packet
import sys
import cPickle as pickle
import time
from random import randrange
from threading import Thread
import socket as s
import hashlib


server = Server('127.0.0.1', '8888')
totalSize = 0
seqNo = 0

def generateCheckSum(packet):
    packetContents = packet.data + str(packet.length) + str(packet.seqNo)
    return hashlib.md5(packetContents).hexdigest()


def generateAckCheckSum(ack):
    ackContents = str(ack.ackNumber) + str(ack.length)
    return hashlib.md5(ackContents).hexdigest()


def toggleSeqNo():
    global seqNo
    if seqNo == 0:
        seqNo = 1
    else:
        seqNo = 0
    return seqNo


def createPackets(chunk):
    global totalSize
    global seqNo
    size = sys.getsizeof(chunk) + sys.getsizeof(seqNo)
    packet = Packet(size, seqNo, chunk)
    toggleSeqNo()
    totalSize += size
    checkSum = generateCheckSum(packet)
    packet.ckSum = checkSum
    return packet


def openAndChunkFile(fileName):
    chunks = []
    try:
        f = open(fileName, 'r')
    except:
        # server.serverSocket.send("404 Not Found")
        server.serverSocket.close()
        return
    while True:
        data = f.readline(512)
        if not data:
            break
        chunks.append(data)
    return chunks


def waitForAck(seqNo, data_string, addr, socket):
    try:
        msg = socket.recvfrom(1024)
    except s.timeout:
        socket.sendto(data_string, addr)
        return 0
    serialized_data = msg[0]
    Ack = pickle.loads(serialized_data)
    if Ack.ackNumber == seqNo and Ack.ckSum == generateAckCheckSum(Ack):
        return 0
    else:
        return 1


def handleRequest(fileName,addr):
    global totalSize
    global seqNo
    totalSize = 0
    dataChunks = openAndChunkFile(fileName)
    finalPackets = []
    sending_server = Server('127.0.0.1', randrange(3000, 4000))

    for chunk in dataChunks:
        finalPackets.append(createPackets(chunk))

    sending_server.serverSocket.sendto(str(totalSize), addr)

    start = time.time()
    for packet in finalPackets:
        receiving_probability = 95

        data_string = pickle.dumps(packet, -1)

        if randrange(0, 100) < receiving_probability:
            sending_server.serverSocket.sendto(data_string, addr)

        ackResponse = waitForAck(packet.seqNo, data_string, addr, sending_server.serverSocket)

        while ackResponse:
            print "waiting for Ack\n"
            ackResponse = waitForAck(packet.seqNo, data_string, addr, sending_server.serverSocket)

        print "Ack Received seq : " + str(packet.seqNo)

    print "sent file in ", (time.time() - start), " seconds. "


while 1:

    msg = None
    # keep receiving and ignore timeout by waiting
    while not msg:
        try:
            msg = server.serverSocket.recvfrom(1024)
        except:
            pass

    fileName, addr = msg

    if not fileName:
        break

    reply = 'OK...' + fileName

    server.serverSocket.sendto(reply, addr)
    print 'Message[' + addr[0] + ':' + str(addr[1]) + '] - ' + fileName.strip()
    Thread(target=handleRequest, args=[fileName,addr]).start()
