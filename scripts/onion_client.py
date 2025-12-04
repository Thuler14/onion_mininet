
import socket, threading

def recv_loop(sock):
    while True:
        data = sock.recv(1024)
        if not data:
            break
        print("SERVER:", data.decode())

sock = socket.socket()
sock.connect(("10.0.4.10", 9000))
print("Connected to server.")

threading.Thread(target=recv_loop, args=(sock,), daemon=True).start()

while True:
    msg = input("")
    sock.send(msg.encode())
