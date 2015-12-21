import threading, ntplib, socket
from pack import PacketOut

ACK_WAIT_TIME = 1.0

# Thread for sending the data packets. It sends the packet, get's into sleep for some time, checks
# if acknowledge has been received. If yes it exits, else it doubles the time to sleep and resends
# the packet. Does this until timeToSleep has reached 1 second.
class Client(threading.Thread):
    def __init__(self, message, application):
        threading.Thread.__init__(self)
        global app
        app = application
        self.message = message
        self.packet = PacketOut(self.message)   # Create new packet instance with the message
        app.dataSequence += 1
        # Take a copy of dataSequence because it may be changed the same time by other running
        # threads
        self.tmpDataSequence = app.dataSequence
        self.packet.setSequenceNumber(self.tmpDataSequence) # Set sequence number
        app.dataSeqForAckList.append(self.tmpDataSequence)  # Put it in the list for acknowledge
        # Create variables for counting the time
        self.timeToSleep = 0.01
        self.newTime = 0
        self.timestamp = self.oldTime = ntplib.time.time()
        self.packet.setTimeStamp(app.toNTPTime(self.timestamp)) # Set timestamp to the packet

    def run(self):
        global app
        global status
        while True:
            try:
                app.serverSock.sendto(self.packet.getTotalPacket(), (app.currentIP,
                                                                     app.REMOTE_PORT))
                if app.DEBUG:
                    app.packetDebug(self.packet)
                ntplib.time.sleep(self.timeToSleep)
                self.timeToSleep *= 2
                if self.tmpDataSequence not in app.dataSeqForAckList:
                    # The server socket has found that an acknowledge is received and removed the
                    # sequence number from the list. So we exit.
                    break
                if self.newTime > ACK_WAIT_TIME:
                    # The "time out" has been reached so the packet won't be sent again
                    app.insert_text('Server ==> Unpredicted disconnection..')
                    status = 1
                    app.statusRefresh()
                    break
            except socket.error as err:
                if err.errno == socket.errno.ENETUNREACH:
                    debugThread = app.setDebug('Network Unreachable')
                    debugThread.start()
                    status = 0
                    app.statusRefresh()
            except socket.gaierror:
                debugThread = app.setDebug('Problem with DNS resolution')
                debugThread.start()
            except UnicodeError:
                debugThread = app.setDebug('Please provide a valid IP or hostname')
                debugThread.start()
            # Renewing the time to sleep
            timeLap = ntplib.time.time() - self.oldTime
            self.oldTime = ntplib.time.time()
            self.newTime += timeLap
