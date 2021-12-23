from threading import Thread, Lock
from getpass4 import getpass
import socket
import sys
import logging
import pickle
import time
import os
import base64


lock = Lock()

class Client:
    def __init__(self, server_ip, server_port):
        self.server_ip = server_ip
        self.server_port = server_port
        self.client_storage = os.path.join(os.getcwd(), "client_storage")
        self.server_connection()
        self.server_sync()

    def server_connection(self):
        # Соединение с сервером
        sock = socket.socket()
        try:
            sock.connect((self.server_ip, self.server_port))
        except ConnectionRefusedError:
            print(f"Не удалось присоединиться к серверу {self.server_ip, self.server_port}")
            sys.exit(0)
        self.sock = sock
        print(f"Установлено соединение с сервером ('{self.server_ip}', {self.server_port})")
        logging.info(
            f"Установлено соединение {self.sock.getsockname()} с сервером ('{self.server_ip}', {self.server_port})")

    def server_sync(self):
        # Вызов функций при получении команд (статусов) от сервера
        Thread(target=self.receive_data).start()
        print("'exit' - разорвать соединение, 'shutdown' - выключить сервер")
        self.status = None
        while True:
            if self.status:
                if self.status == "auth":
                    self.auth()
                elif self.status == "register":
                    self.register()
                    logging.info(f"Пользователь {self.sock.getsockname()} успешно зарегистрировался")
                elif self.status == "passwd":
                    self.send_passwd()
                elif self.status == "success":
                    self.success()
                elif self.status == "server_client":
                    raw_data, file_name = self.data[0], self.data[1]
                    self.server_client_transfer(file_name, raw_data)
                else:
                    user_input = input(f"{self.username}> ")
                    if user_input != "":
                        if user_input == "pwd":
                            pwd = pickle.dumps(["pwd", "Текущая директория", self.username])
                            self.sock.send(pwd)
                        elif user_input == "ls":
                            ls = pickle.dumps(["ls", "Файлы в директории", self.username])
                            self.sock.send(ls)
                        elif user_input == "mkdir":
                            mkdir = pickle.dumps(["mkdir", str(input("Введите название новой директории: ")), self.username])
                            self.sock.send(mkdir)
                        elif user_input == "rmdir":
                            rmdir = pickle.dumps(["rmdir", str(input("Введите название директории для удаления: ")), self.username])
                            self.sock.send(rmdir)
                        elif user_input == "rm":
                            rm = pickle.dumps(["rm", str(input("Введите название файла для удаления: ")), self.username])
                            self.sock.send(rm)
                        elif user_input == "rename":
                            rename = pickle.dumps(["rename", [str(input("Введите название файла, чтобы переименовать: ")),
                                                              str(input("Введите новое название файла: "))], self.username])
                            self.sock.send(rename)
                        elif user_input == "cat":
                            file_name = str(input("Введите название файла чтобы прочитать: "))
                            cat = pickle.dumps(["cat", file_name, self.username])
                            self.sock.send(cat)
                        elif user_input == "cd":
                            directory_name = str(input("Введите название директории чтобы переместиться: "))
                            cd = pickle.dumps(["cd", directory_name, self.username])
                            self.sock.send(cd)
                        elif user_input == "cd ..":
                            cd_up = pickle.dumps(["cd ..", "move up", self.username])
                            self.sock.send(cd_up)
                        elif user_input == "copy to server":
                            file_name = str(input(
                                "Введите название файла в директории client_storage для копирования на сервер: "))
                            copy_client_server = pickle.dumps(["client_server", [self.client_server_transfer(file_name), file_name], self.username])
                            self.sock.send(copy_client_server)
                        elif user_input == "copy from server":
                            ls = pickle.dumps(
                                ["ls", "Файлы в директории", self.username])
                            self.sock.send(ls)
                            file_name = str(input("Введите название файла чтобы скопировать с сервера в директорию client_storage: "))
                            copy_server_client = pickle.dumps(["server_client", file_name, self.username])
                            self.sock.send(copy_server_client)
                        elif user_input == "exit":
                            print(f"Разрыв соединения {self.sock.getsockname()} с сервером по команде")
                            logging.info(f"Разрыв соединения {self.sock.getsockname()} с сервером по команде")
                            close_connection = pickle.dumps(["exit", "Разрыв соединения", self.username])
                            self.sock.send(close_connection)
                            self.sock.close()
                            sys.exit(0)
                        elif user_input == "shutdown":
                            shutdown_server = pickle.dumps(["shutdown", "Отключение сервера", self.username])
                            self.sock.send(shutdown_server)
                        else:
                            # Отправляем сообщение и имя клиента
                            send_message = pickle.dumps(["message", user_input, self.username])
                            self.sock.send(send_message)
                            logging.info(f"Отправка данных от {self.sock.getsockname()} на сервер: {user_input}")

    def receive_data(self):
        # Поток получения и обработки данных от сервера
        # Клиент принимает пакет вида ["status", "message"]
        while True:
            try:
                self.data = self.sock.recv(1024)
                if not self.data:
                    sys.exit(0)
                self.status = pickle.loads(self.data)[0]
                # Вывод сообщений от других пользователей
                if self.status == "message":
                    print(f"\n{pickle.loads(self.data)[2]}->", pickle.loads(self.data)[1])
                    logging.info(f"{self.sock.getsockname()} получил данные от сервера: {pickle.loads(self.data)[1]}")
                else:
                    self.data = pickle.loads(self.data)[1]
            except OSError:
                break

    def server_client_transfer(self, file_name, file_content):
        # Копирование файла с сервера на клиент
        try:
            data = base64.b64decode(file_content)
            with open(f"{self.client_storage}{os.sep}{file_name}", "w+") as f:
                f.write(data.decode("utf-8"))
        except Exception as e:
            logging.error(str(e))

    def client_server_transfer(self, file_name):
        try:
            with open(f"{self.client_storage}{os.sep}{file_name}", "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        except (FileNotFoundError, IndexError, IsADirectoryError):
            logging.error("Произошла ошибка при копировании файла с клиента на сервер")

    def send_passwd(self):
        # Отправка пароля на сервер
        passwd = input('ps>')
        self.sock.send(pickle.dumps(["passwd", passwd]))
        time.sleep(0.25)

    def auth(self):
        self.username = input("Введите имя пользователя: ")
        self.sock.send(pickle.dumps(["auth", self.username]))
        time.sleep(0.25)

    def register(self):
        self.username = input("Введите новое имя пользователя: ")
        print(["register", self.username])
        self.sock.send(pickle.dumps(["register", self.username]))
        time.sleep(0.25)

    def success(self):
        # Вывод сообщения об успешной регистрации или авторизации
        print(self.data)
        self.status = "ready"
        self.username = self.data.split(" ")[2]
        logging.info(f"Клиент {self.sock.getsockname()} прошел авторизацию")


def ip_validation(ip):
    if ip == "":
        return False
    else:
        try:
            octets = ip.split(".", 4)
            if len(octets) == 4:
                for octet in octets:
                    octet = int(octet)
                    if 0 <= octet <= 255:
                        pass
                    else:
                        return False
            else:
                return False
        except ValueError:
            return False
        return True


def port_validation(port):
    try:
        value = int(port)
        if 1 <= value <= 65535:
            return True
        print(f"Неправильное значение - {value} для порта")
        return False
    except ValueError:
        print(f"{port} - не число")
        return False


logging.basicConfig(filename='logs/client.log',
                    format="%(asctime)s [%(levelname)s] %(funcName)s: %(message)s", level=logging.INFO)


def main():
    user_port = input("Введите порт сервера (enter для значения по умолчанию):")
    user_ip = input("Введите IP-адрес сервера (enter для значения по умолчанию):")
    # Валидация порта и IP адреса клиента
    if not port_validation(user_port):
        user_port = 9090
        print(f"Установлен порт {user_port} по умолчанию")
    if not ip_validation(user_ip):
        user_ip = "127.0.0.1"
        print(f"Установлен IP-адрес {user_ip} по умолчанию")
    Client(user_ip, int(user_port))


if __name__ == "__main__":
    main()
