
import socket, threading

def recv_loop(conn):
    while True:
        data = conn.recv(1024)
        if not data:
            break
        print("CLIENT:", data.decode())

def send_loop(conn):
    while True:
        msg = input("")
        conn.send(msg.encode())

s = socket.socket()
s.bind(("0.0.0.0", 9000))
s.listen(1)
print("Server ready...")
conn, addr = s.accept()
print("Connected with:", addr)

threading.Thread(target=recv_loop, args=(conn,), daemon=True).start()
send_loop(conn)
