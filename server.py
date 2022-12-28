import threading
import socket
import FileSystem
import json

fs = FileSystem.FileSystem()

class Logger:
    def __init__(self):
        self.log_file = open("log.txt", "w")

    def info(self, message):
        self.log_file.write(f"INFO: {message}\n")
    
    def error(self, message):
        self.log_file.write(f"ERROR: {message}\n")

class Executor:
    """
    Commands:
        mkdir <path> - creates a directory at path
        touch <path> - creates a file at path
        ls <path> - lists the contents of the directory at path
        mv <old_path> <new_path> - moves the file or directory at old_path to new_path
        rm <path> - removes the file or directory at path
        open <path> r/w - opens the file at path for reading or writing
        close <path> - closes the file at path
        write <data> - writes data to the file at opened path
        read <path> - reads data from the file at opened path
        visualize - prints the file system in a tree format
    """

    def __init__(self):
        self.logger = Logger()

    def __split_command(self, command):
        """split the command on whitespaces into a list, 
        also text within quotations is treated as a single element"""
        command = command.split()
        new_command = []
        for i in command:
            if i[0] == '"' and i[-1] == '"':
                new_command.append(i[1:-1])
            else:
                new_command.append(i)
        return new_command

    def execute(self, user: 'User', command):
        self.logger.info(f"{user.name}: {command}")
        command = self.__split_command(command)
        response = ""
        try:
            if command[0] == "mkdir":
                fs.mkdir(command[1])
                response = f"Directory {command[1]} created."
                self.logger.info(f"{user.name}: {response}")
            elif command[0] == "touch":
                fs.touch(command[1])
                response = f"File {command[1]} created."
                self.logger.info(f"{user.name}: {response}")
            elif command[0] == "open":
                fs.open(command[1], command[2])
                response = f"File {command[1]} opened for {command[2]}."
                self.logger.info(f"{user.name}: {response}")
            elif command[0] == "close":
                fs.close(command[1])
                response = f"File {command[1]} closed."
                self.logger.info(f"{user.name}: {response}")
            elif command[0] == "write":
                fs.write(command[1], command[2])
                response = f"Data written to file {command[1]}."
                self.logger.info(f"{user.name}: {response}")
            elif command[0] == "read":
                response = fs.read(command[1])
                self.logger.info(f"{user.name}: {response}")
            elif command[0] == "ls":
                response = fs.ls(command[1])
                self.logger.info(f"{user.name}: {response}")
            elif command[0] == "mv":
                fs.mv(command[1], command[2])
                response = f"File {command[1]} moved to {command[2]}."
                self.logger.info(f"{user.name}: {response}")
            elif command[0] == "rm":
                fs.delete(command[1])
                response = f"File {command[1]} deleted."
                self.logger.info(f"{user.name}: {response}")
            elif command[0] == "vtree":
                response = fs.visualise_tree()
                self.logger.info(f"{user.name}: Tree visualised.")
            elif command[0] == "vmap":
                response = fs.visualise_mmap()
                self.logger.info(f"{user.name}: Map visualised.")
            else:
                raise Exception("Invalid command. Please try again.")
        except Exception as e:
            response = str(e)
            self.logger.error(f"{user.name}: {response}")
        
        return response

class User:
    def __init__(self, name):
        self.name = name
        self.current_dir = ""

    def __repr__(self):
        return self.name


executor = Executor()

# A thread function to handle a client connection


def handle_client(client_socket: socket.socket):
    # Do something with the client's data here
    info = client_socket.getpeername()
    
    name = client_socket.recv(1024).decode()
    user = User(name)
    print(f"Client {info} connected as {user.name}")

    # send welcome message
    client_socket.send(f"Welcome {user.name}!".encode())

    while True:
        request = client_socket.recv(1024)
        if request == b'exit':
            executor.logger.info(f"{user.name}: Disconnected.")
            break
        
        response = executor.execute(user, request.decode())

        client_socket.send(response.encode())

        with open("state.json", "w") as f:
            json.dump(fs.store_state(), f)

    client_socket.close()
    print(f"Client {info} as {user.name} disconnected")


# Create a TCP/IP socket
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Bind the socket to the address and port
server_socket.bind(("localhost", 95))

# Listen for incoming connections
server_socket.listen(5)

# Load state if exists
try:
    print("Loading state... ")
    with open("state.json", "r") as f:
        fs.load_state(json.load(f))
except Exception as e:
    print("No state found. Continuing with empty fs... ")
    print(str(e))
    fs = FileSystem.FileSystem()
    

while True:
    # Accept a new connection
    (client_socket, client_address) = server_socket.accept()

    # Start a new thread to handle the client
    client_thread = threading.Thread(
        target=handle_client, args=(client_socket,))
    client_thread.start()

    # break on SIGINT
    try:
        pass
    except KeyboardInterrupt:
        print("Storing state... ")
        with open("state.json", "w") as f:
            f.write(fs.store_state())
        
        print("Shutting down... ")
        break
