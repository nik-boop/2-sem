import base64
from threading import Thread
from tabulate import tabulate
import shutil
import socket
import json
import pickle
import logging
import hashlib
import os


class Server:
    def __init__(self, port):
        self.database = "./users.json"
        self.working_directory = os.path.join(os.getcwd(), "server_storage")
        self.path_length = len(self.working_directory.split("/"))
        self.server_port = port
        self.users = []
        self.connections = []
        self.init_server()

    def init_server(self):
        # Инициализация сервера
        sock = socket.socket()
        sock.bind(('', self.server_port))
        sock.listen(5)
        self.sock = sock
        logging.info(f"Старт сервера, порт: {self.server_port}")
        while True:
            conn, addr = self.sock.accept()
            Thread(target=self.client_logic, args=(conn, addr)).start()
            logging.info(f"Подключение клиента {addr}")
            self.connections.append(conn)

    def broadcast(self, msg, conn, username):
        # Отправка сообщений всем клиентам (чат)
        try:
            if len(self.connections) > 1:
                for connection in self.connections:
                    if connection != conn:
                        connection.send(
                            pickle.dumps(["message", msg, username]))
                        logging.info(
                            f"Отправка данных клиенту {connection.getsockname()}: {msg}")
        except IOError as e:
            for connection in self.connections:
                if connection != conn:
                    self.connections.remove(connection)

    def client_server_transfer(self, file_name, file_data, conn):
        # Получение файла от клиента и запись в директорию
        try:
            file_content = base64.b64decode(file_data).decode("utf-8")
            with open(f"{self.working_directory}/{file_name}", "w+") as f:
                f.write(file_content)
            conn.send(pickle.dumps(
                ["message", f"Файл {file_name} успешно перенесён на сервер",
                 "~SERVER~"]))
        except Exception as e:
            conn.send(pickle.dumps(["message", str(e), "~SERVER~"]))

    def server_client_transfer(self, file_name, conn):
        # Передача файла с сервера на клиент (набор байтов)
        try:
            with open(f"{self.working_directory}/{file_name}", "rb") as f:
                data = base64.b64encode(f.read())
            conn.send(
                pickle.dumps(["server_client", [data, file_name], "~SERVER~"]))
        except Exception as e:
            conn.send(pickle.dumps(["message", str(e), "~SERVER~"]))

    def client_logic(self, conn, address):
        # Поток прослушивания клиентов
        self.authorization(address, conn)
        while True:
            try:
                data = conn.recv(1024)
            except ConnectionResetError:
                conn.close()
                self.connections.remove(conn)
                logging.info(f"Отключение клиента {address}")
                break
            if data:
                status, data, username = pickle.loads(data)
                logging.info(
                    f"Прием данных от клиента '{username}_{address[1]}': {data}")
                if status == "message":
                    self.broadcast(data, conn, username)
                elif status == "pwd":
                    logging.info(
                        f"{username} запросил показать текущую директорию")
                    conn.send(pickle.dumps(
                        ["message", self.working_directory, "~SERVER~"]))
                elif status == "ls":
                    logging.info(
                        f"{username} запросил показать файлы в директории")
                    list_dir = []
                    for each in os.scandir(path=self.working_directory):
                        object_data = f' - Directory - {each.name}' if each.is_dir() else f' - File - {each.name}'
                        object_info = object_data.split(' - ')
                        object_info.pop(0)
                        list_dir.append(object_info)
                    dir_data = tabulate((i for i in list_dir), tablefmt="pipe")
                    conn.send(pickle.dumps(["message", dir_data, "~SERVER~"]))
                elif status == "mkdir":
                    directory_name = data
                    logging.info(
                        f"{username} запросил создать новую директорию {directory_name}")
                    if not os.path.exists(
                            f'{self.working_directory}/{directory_name}'):
                        os.makedirs(
                            f'{self.working_directory}/{directory_name}')
                        conn.send(pickle.dumps(["message",
                                                f'Директория "{directory_name}" успешно создана',
                                                "~SERVER~"]))
                    else:
                        conn.send(pickle.dumps(["message",
                                                f'Директория "{directory_name}" уже существует',
                                                "~SERVER~"]))
                elif status == "rmdir":
                    directory_name = data
                    logging.info(
                        f"{username} запросил удалить директорию {directory_name}")
                    try:
                        shutil.rmtree(
                            f"{self.working_directory}/{directory_name}")
                    except OSError as e:
                        conn.send(pickle.dumps(
                            ["message", f"Ошибка: {e.filename} - {e.strerror}",
                             "~SERVER~"]))
                    else:
                        conn.send(pickle.dumps(["message",
                                                f'Директория "{directory_name}" успешно удалена',
                                                "~SERVER~"]))
                elif status == "rm":
                    file_name = data
                    logging.info(
                        f"{username} запросил удалить файл {file_name}")
                    try:
                        os.remove(f"{self.working_directory}/{file_name}")
                    except OSError as e:
                        conn.send(pickle.dumps(
                            ["message", f"Ошибка: {e.filename} - {e.strerror}",
                             "~SERVER~"]))
                    else:
                        conn.send(pickle.dumps(
                            ["message", f'Файл "{file_name}" успешно удалён',
                             "~SERVER~"]))
                elif status == "rename":
                    file_name, new_file_name = data[1][0], data[1][1]
                    logging.info(
                        f"{username} запросил переименовать файл {file_name} в {new_file_name}")
                    try:
                        os.rename(f"{self.working_directory}/{file_name}",
                                  f"{self.working_directory}/{new_file_name}")
                    except OSError as e:
                        conn.send(pickle.dumps(
                            ["message", f"Ошибка: {e.filename} - {e.strerror}",
                             "~SERVER~"]))
                    else:
                        conn.send(pickle.dumps(["message",
                                                f'Файл "{file_name}" успешно переименован в "{new_file_name}"',
                                                "~SERVER~"]))
                elif status == "cat":
                    file_name = data
                    logging.info(
                        f"{username} запросил прочитать файл {file_name}")
                    try:
                        with open(f"{self.working_directory}/{file_name}",
                                  "r") as f:
                            text = f.read()
                        conn.send(pickle.dumps(["message", text, "~SERVER~"]))
                    except FileNotFoundError:
                        conn.send(pickle.dumps(
                            ["message", f"Файл {file_name} не существует"]))
                elif status == "cd":
                    directory_name = data
                    move_path = self.working_directory + f"/{directory_name}"
                    if os.path.isdir(move_path):
                        self.working_directory += f"/{directory_name}"
                        os.chdir(self.working_directory)
                        conn.send(pickle.dumps(["message",
                                                f"Успешный переход в директорию {directory_name}"
                                                f"\nТекущий путь: {self.working_directory}",
                                                "~SERVER~"]))
                elif status == "cd ..":
                    location = self.working_directory.split("/")
                    if self.path_length < len(location):
                        location.pop()
                        up = "/".join(location)
                        self.working_directory = up
                        os.chdir(self.working_directory)
                        conn.send(pickle.dumps(["message",
                                                f"Успешный переход в директорию {location[-1]}"
                                                f"\nТекущий путь: {self.working_directory}",
                                                "~SERVER~"]))
                    else:
                        conn.send(pickle.dumps(["message",
                                                "Ошибка доступа!\nНевозможно переместиться"
                                                " выше заданной корневой директории (server_storage)",
                                                "~SERVER~"]))
                elif status == "client_server":
                    file_data, file_name = data[0], data[1]
                    self.client_server_transfer(file_name, file_data, conn)
                elif status == "server_client":
                    file_name = data
                    self.server_client_transfer(file_name, conn)
                elif status == "shutdown":
                    for connection in self.connections:
                        connection.send(pickle.dumps(
                            ["message", f"{username} выключил сервер",
                             "~SERVER~"]))
                        connection.close()
                    logging.info(f"Отключение сервера по команде")
                    self.sock.close()
                    break
                elif status == "exit":
                    logging.info(f"Закрытие соединения с клиентом {username}")
                    conn.close()
                    self.connections.remove(conn)
                    for connection in self.connections:
                        connection.send(pickle.dumps(
                            ["message", f"{username} отключился от сервера",
                             "~SERVER~"]))
                    break
            else:
                # Закрываем соединение
                conn.close()
                self.connections.remove(conn)
                logging.info(f"Отключение клиента {address}")
                break

    def authorization(self, addr, conn):
        # Авторизация пользователей
        print(1)
        conn.send(pickle.dumps(["auth", "Введите имя пользователя: "]))
        username = pickle.loads(conn.recv(1024))[1]
        try:
            # Данные пользователей из файла
            self.users = self.database_read()

        except json.decoder.JSONDecodeError:
            # Первичная запись в пустой файл
            self.registration(addr, conn, username)
        is_registered = False
        for user in self.users:
            for key, value in user.items():
                if key == username:
                    is_registered = True
                    password = value['password']
                    conn.send(
                        pickle.dumps(["passwd", "Введите свой пароль: "]))
                    passwd = pickle.loads(conn.recv(1024))[1]
                    # Проверка пароля
                    if self.check_password(passwd, password):
                        conn.send(pickle.dumps(
                            ["success", f"Добро пожаловать, {username}"]))
                    else:
                        # Если пароль неверный снова отправляем на авторизацию
                        self.authorization(addr, conn)
                    logging.info(
                        f"Клиент {self.sock.getsockname()} успешно авторизировался")
        if not is_registered:
            self.registration(addr, conn, username)

    def registration(self, addr, conn, username):
        # Регистрация пользователя с новым username
        conn.send(pickle.dumps(["passwd", "Введите новый пароль: "]))
        passwd = self.generate_hash(pickle.loads(conn.recv(1024))[1])
        conn.send(
            pickle.dumps(["success", f"Успешная регистрация, {username}"]))
        self.users.append({username: {'password': passwd, 'address': addr[0]}})
        # Запись в файл при регистрации пользователя
        logging.info(
            f"Клиент {self.sock.getsockname()} успешно зарегистрировался")
        self.database_write()
        self.users = self.database_read()

    def database_read(self):
        with open(self.database, 'r') as f:
            users = json.load(f)
        return users

    def database_write(self):
        with open(self.database, 'w') as f:
            json.dump(self.users, f, indent=4)

    def check_password(self, user_input, real_password):
        # Проверка пароля
        key = hashlib.md5(user_input.encode() + b'salt').hexdigest()
        correct_password = user_input == real_password
        return correct_password

    def generate_hash(self, passwd):
        # Генерация хеша для безопасного хранение паролей
        key = hashlib.md5(passwd.encode() + b'salt').hexdigest()
        return key


def is_available_port(port):
    try:
        sock = socket.socket()
        sock.bind(("", port))
        sock.close()
        logging.info(f"Порт {port} свободен")
        return True
    except OSError:
        logging.info(f"Порт {port} занят")
        return False


logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(funcName)s: %(message)s",
    handlers=[logging.FileHandler("logs/server.log"), logging.StreamHandler()],
    level=logging.INFO)


def main():
    server_port = 9090  # порт по умолчанию
    # Если порт по умолчанию занят, то перебираем порты
    if not is_available_port(server_port):
        logging.info(f"Порт по умолчанию {server_port} занят")
        port_available = False
        while not port_available:
            server_port += 1
            port_available = is_available_port(server_port)
    Server(server_port)


if __name__ == "__main__":
    main()
