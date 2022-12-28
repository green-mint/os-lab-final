import socket

def print_protocol():
    print("mkdir <path> - creates a directory at path")
    print("touch <path> - creates a file at path")
    print("ls <path> - lists the contents of the directory at path")
    print("mv <old_path> <new_path> - moves the file or directory at old_path to new_path")
    print("rm <path> - removes the file or directory at path")
    print("open <path> r/w - opens the file at path for reading or writing")
    print("close <path> - closes the file at path")
    print("write <path> <data> - writes data to the file at opened path")
    print("read <path> - reads data from the file at opened path")
    print("vtree - prints the file system in a tree format")
    print("vmap - prints the memory map of the file system")
    print("help - prints this message")
    print("exit - exits the program")

def get_command():
    while True:    
        
        print("\nEnter a command: ", end="")

        command = input()
        command = command.split(" ")

        if command[0] == "help":
            print_protocol()
            continue
        else:
            return command




# Create a TCP/IP socket
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

server = input("Enter the server address: ")

# Connect the socket to the server
client_socket.connect((server, 95))

# ask for name of the client and send it to the server
name = input("Enter your name: ")
client_socket.send(name.encode())

# wait for the server to send the welcome message
data = client_socket.recv(1024)
print(data.decode())

print_protocol()

while True:
    # Send data
    command = get_command()

    if command[0] == "exit":
        client_socket.send("exit".encode())
        break

    client_socket.send(" ".join(command).encode())

    # Receive data
    data = client_socket.recv(1024)
    print("Received: " + data.decode() + "\n")

# Close the socket
client_socket.close()