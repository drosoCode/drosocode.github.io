import socket
from fdp import ForzaDataPacket
from matplotlib import pyplot
import time

# Create a UDP socket
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# Bind the socket to the port
server_address = ("127.0.0.1", 1010)
s.bind(server_address)
print("Do Ctrl+c to exit the program !!")

props = []
arr = []
t_max = time.time() + 30

props = ["speed"]
# accel, brake, handbrake -> 1 or 0
# current_engine_rpm [10 000], power [500 000]
# speed [200], race_pos [0,10]
for i in range(len(props)):
    arr.append([])

while time.time() < t_max:
    print("####### Server is listening #######")
    data, address = s.recvfrom(1024)
    df = ForzaDataPacket(data, "fh4")

    d = df.to_list(props)
    for i in range(len(d)):
        arr[i].append(d[i])

for i in range(len(props)):
    pyplot.plot(list(range(len(arr[i]))), arr[i], label=props[i])
pyplot.legend()
pyplot.show()