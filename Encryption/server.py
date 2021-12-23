import random
import pickle
import socket
import time


def Cenc(mes, k):
    return [chr((ord(i) + k)%65536)for i in mes]

def Cdec(mes, k):
    return [chr((65536 + (ord(i) - k) % 65536) % 65536) for i in mes]

class Cryptographer:
    def __init__(self, g=12, p=80, rmin=1, rmax=10):
        self.g = g
        self.p = p
        self.secret_key = random.randint(rmin, rmax)

    def CreateOpenKey(self):
        '''Создает секретный ключ'''
        self.open_key = self.g ** self.secret_key % self.p
        return self.open_key, self.g, self.p

    def Decrypt(self, B):
        '''Получает общий секретный ключ K'''
        return B ** self.secret_key % self.p

    def CreateSharedKey(self, A, g, p):
        '''Получает внешний открытый ключ, создает свой открытый ключ, а также обший секретный'''
        return g ** self.secret_key % p, A ** self.secret_key % p

Cr = Cryptographer()
sock = socket.socket()
print(f'---\nStart Server')
ip = ''
port = 9090
sock.bind((ip, port))
print(f'Open socket\nip: {ip}\nport: {port}')

sock.listen(1)
print(f'Listening socket')

conn, addr = sock.accept()
print(f'Accept new connection\nconn: {conn}\naddress: {addr}')

data = conn.recv(1024)
data = pickle.loads(data)
if data[0] == 'open_key':
    OpenKey = data[1]
print(f'Get Client open key: {OpenKey}')

(B, K) = Cr.CreateSharedKey(*OpenKey)
SharedKeyClient = K
conn.send(pickle.dumps(["open_key", Cr.CreateOpenKey(), B]))
print(f'Send Servre open key: {Cr.CreateOpenKey()}\n---')

while True:
    data = conn.recv(1024)
    get_time = time.localtime()
    data = pickle.loads(data)
    K = Cr.Decrypt(data[2])
    mesin = data[1]
    print(f'Получено: {mesin}')
    print(f'Encryption')
    mesin = ''.join(Cdec(Cdec(mesin, K), SharedKeyClient))
    print(mesin)
    print(f'---')
    if "exit" in mesin.lower():
        conn.close()
        exit()

    mesout = f'{time.strftime("%d %m %Y %H:%M:%S", get_time)} :: Client {addr} send message :: {mesin}'
    data = ["message", Cenc(Cenc(mesout, K), SharedKeyClient)]

    conn.send(pickle.dumps(data))
    print(f"Send message {mesout}\n---")
    if "exit" in mesout.lower():
        conn.close()
        exit()
