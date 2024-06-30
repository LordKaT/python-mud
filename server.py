import select, signal, socket, sys, time

class Server(object):
    class _Client(object):
        socket = None
        address = None
        buffer = None
        check = 0

        def __init__(self, socket, address, buffer, check) -> None:
            self.socket = socket
            self.address = address
            self.buffer = buffer
            self.check = check
        
    EVENT_NEW_PLAYER = 1
    EVENT_PLAYER_LEFT = 2
    EVENT_COMMAND = 3

    READ_STATE_NORMAL = 1
    READ_STATE_COMMAND = 2
    READ_STATE_SUBNEG = 3

    TN_INTERPRET_AS_COMMAND = 255
    TN_PING = 246
    TN_WILL = 251
    TN_WONT = 252
    TN_DO = 253
    TN_DONT = 254
    TN_SUBNEG_START = 250
    TN_SUBNEG_END = 240
    TN_INTERRUPT_PROCESS = 244

    listener = None
    clients = {}
    idcounter = 0
    events = []
    new_events = []

    def __init__(self) -> None:
        self.clients = {}
        self.idcounter = 0
        self.events = []
        self.new_events = []

        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.listener.bind(("0.0.0.0", 2400))
        self.listener.setblocking(False)
        self.listener.listen(1)
    
    def update(self) -> None:
        self._check()

        self.events = list(self.new_events)
        self.new_events = []
    
    def get_new_players(self) -> list:
        retval = []
        for ev in self.events:
            if ev[0] == self.EVENT_NEW_PLAYER:
                retval.append(ev[1])
        return retval
    
    def get_disconnected_players(self) -> list:
        retval = []
        for ev in self.events:
            if ev[0] == self.EVENT_PLAYER_LEFT:
                retval.append(ev[1])
        return retval
    
    def get_commands(self) -> list:
        retval = []
        for ev in self.events:
            if ev[0] == self.EVENT_COMMAND:
                retval.append((ev[1], ev[2], ev[3]))
        return retval
    
    def send_message(self, to, message) -> None:
        self.attempt_send(to, message + "\r\n")
    
    def shutdown(self) -> None:
        for cl in self.clients.values():
            cl.socket.shutdown(socket.SHUT_RDWR)
            cl.socket.close()
        self.listener.close()
    
    def attempt_send(self, clid, data) -> None:
        try:
            self.clients[clid].socket.sendall(bytearray(data, "latin1"))
        except KeyError:
            pass
        except socket.error:
            self.handle_disconnect(clid)

    def _check(self) -> None:
        # check new connections
        rlist, wlist, xlist = select.select([self.listener], [], [], 0)
        if self.listener in rlist:
            joined_socket, addr = self.listener.accept()
            joined_socket.setblocking(False)
            self.clients[self.idcounter] = Server._Client(joined_socket, addr[0], "", time.time())
            self.new_events.append((self.EVENT_NEW_PLAYER, self.idcounter))
            self.idcounter += 1
        
        for id, cl in list(self.clients.items()):
            # check for disconnection
            if time.time() - cl.check >= 5.0:
                self.attempt_send(id, "\x00")
                cl.check = time.time()

            rlist, wlist, xlist = select.select([cl.socket], [], [], 0)
            if cl.socket not in rlist:
                continue

            try:
                data = cl.socket.recv(4096).decode("latin1")
                message = self.process_data(id, cl, data)
                if message:
                    message = message.strip()
                    command, params = (message.split(" ", 1) + ["", ""])[:2]
                    self.new_events.append((self.EVENT_COMMAND, id, command.lower(), params))
            except socket.error:
                self.handle_disconnect(id)
    
    def handle_disconnect(self, clid) -> None:
        del(self.clients[clid])
        self.new_events.append((self.EVENT_PLAYER_LEFT, clid))

    def process_data(self, clid, client, data) -> str:
        message = None
        state = self.READ_STATE_NORMAL

        for c in data:
            match state:
                case self.READ_STATE_NORMAL:
                    match c:
                        case "\n":
                            message = client.buffer
                            client.buffer = ""
                        case "\x08":
                            client.buffer = client.buffer[:-1]
                        case _:
                            if ord(c) == self.TN_INTERPRET_AS_COMMAND:
                                state = self.READ_STATE_COMMAND
                            else:
                                client.buffer += c
                case self.READ_STATE_COMMAND:
                    match ord(c):
                        case self.TN_SUBNEG_START:
                            state = self.READ_STATE_SUBNEG
                        case self.TN_INTERRUPT_PROCESS:
                            self.handle_disconnect(clid)
                            return None
                        case _:
                            if ord(c) in (self.TN_WILL, self.TN_WONT, self.TN_DO, self.TN_DONT):
                                state = self.READ_STATE_COMMAND
                            else:
                                state = self.READ_STATE_NORMAL
                case self.READ_STATE_SUBNEG:
                    match ord(c):
                        case self.TN_SUBNEG_END:
                            state = self.READ_STATE_NORMAL
        return message
