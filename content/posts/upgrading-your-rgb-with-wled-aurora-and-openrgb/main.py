
import socket
from openrgb import OpenRGBClient
from openrgb.utils import RGBColor, DeviceType
from numpy import interp

from fdp import ForzaDataPacket
# get fdp.py from https://github.com/nettrom/forza_motorsport

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_address = ("127.0.0.1", 1010)
s.bind(server_address)

print("####### Server is listening #######")


client = OpenRGBClient("127.0.0.1", 6742, "forza")
keyboard = client.get_devices_by_type(DeviceType.KEYBOARD)[0].zones[0]

props = [
    "speed",
    "fuel",
    "race_pos",
    "accel",
    "brake",
    "handbrake",
    "current_engine_rpm",
    "power",
    "tire_slip_ratio_FL",
    "tire_slip_ratio_FR",
    "tire_slip_ratio_RL",
    "tire_slip_ratio_RR",
    "is_race_on",
]


RED = RGBColor(255, 0, 0)
YELLOW = RGBColor(255, 255, 0)
ORANGE = RGBColor(255, 165, 0)
GREEN = RGBColor(0, 255, 0)
CYAN = RGBColor(0, 255, 255)
MAGENTA = RGBColor(255, 0, 255)
BLACK = RGBColor(0, 0, 0)

props_keys = {}
i = 0
for x in props:
    props_keys[x] = i
    i += 1

kb_black_keys = []
for i in range(len(keyboard.matrix_map)):
    for j in keyboard.matrix_map[i]:
        if j is not None:
            kb_black_keys.append(BLACK)


def value2color(val, min, max, inverted=False):
    red = [0, 1, 2, 3, 4]
    orange = [20, 21, 22, 23, 24]
    yellow = [30, 31, 32, 33, 34]
    green = [50, 51, 52, 53, 54]
    if inverted:
        colors = red + orange + yellow + green
    else:
        colors = (
            list(reversed(green))
            + list(reversed(yellow))
            + list(reversed(orange))
            + list(reversed(red))
        )
    return RGBColor.fromHSV(
        colors[round(interp(val, [min, max], [0, len(colors) - 1]))], 100, 100
    )


def keys2band(kb, start_line, start_col, nb):
    band = []
    n = 0
    for i in range(start_col, len(kb.matrix_map[start_line])):
        if kb.matrix_map[start_line][i] is not None:
            band.append(kb.matrix_map[start_line][i])
            n += 1
            if n > nb:
                break
    return band


KB_LINE1 = keys2band(keyboard, 3, 2, 10)
KB_LINE2 = keys2band(keyboard, 4, 2, 10)
KB_LINE3 = keys2band(keyboard, 5, 2, 10)


def value2band(val, val_min, val_max, band, colors):
    max = len(band) - 1
    nb_keys = int(interp(val, [val_min, val_max], [0, max]))
    i = 0
    for x in band[0:nb_keys]:
        colors[x] = value2color(i, 0, max)
        i += 1


client.clear()

while True:
    raw, address = s.recvfrom(1024)
    data = ForzaDataPacket(raw, "fh4").to_list(props)

    keyboard.colors = kb_black_keys.copy()

    if data[props_keys["race_pos"]] != 0:
        key = 10 if data[props_keys["race_pos"]] > 9 else data[props_keys["race_pos"]]
        keyboard.colors[keyboard.matrix_map[2][key]] = value2color(key, 1, 10)

    if data[props_keys["accel"]] > 0:
        keyboard.colors[keyboard.matrix_map[2][19]] = GREEN
        keyboard.colors[keyboard.matrix_map[3][19]] = GREEN
        keyboard.colors[keyboard.matrix_map[4][19]] = GREEN
        keyboard.colors[keyboard.matrix_map[5][19]] = GREEN

    if data[props_keys["brake"]] > 0:
        keyboard.colors[keyboard.matrix_map[2][20]] = CYAN
        keyboard.colors[keyboard.matrix_map[3][20]] = CYAN
        keyboard.colors[keyboard.matrix_map[4][20]] = CYAN
        keyboard.colors[keyboard.matrix_map[5][20]] = CYAN

    if data[props_keys["handbrake"]] > 0:
        keyboard.colors[keyboard.matrix_map[2][21]] = MAGENTA
        keyboard.colors[keyboard.matrix_map[3][21]] = MAGENTA
        keyboard.colors[keyboard.matrix_map[4][21]] = MAGENTA
        keyboard.colors[keyboard.matrix_map[5][21]] = MAGENTA

    if data[props_keys["is_race_on"]] > 0:
        keyboard.colors[keyboard.matrix_map[0][12]] = GREEN
        keyboard.colors[keyboard.matrix_map[0][13]] = GREEN
        keyboard.colors[keyboard.matrix_map[0][14]] = GREEN

    value2band(
        data[props_keys["current_engine_rpm"]], 0, 10000, KB_LINE1, keyboard.colors
    )
    value2band(data[props_keys["speed"]], 0, 100, KB_LINE2, keyboard.colors)
    value2band(data[props_keys["power"]], -500000, 500000, KB_LINE3, keyboard.colors)

    keyboard.colors[keyboard.matrix_map[2][16]] = value2color(
        data[props_keys["tire_slip_ratio_FL"]], -30, 30
    )
    keyboard.colors[keyboard.matrix_map[2][18]] = value2color(
        data[props_keys["tire_slip_ratio_FR"]], -30, 30
    )
    keyboard.colors[keyboard.matrix_map[3][16]] = value2color(
        data[props_keys["tire_slip_ratio_RL"]], -30, 30
    )
    keyboard.colors[keyboard.matrix_map[3][18]] = value2color(
        data[props_keys["tire_slip_ratio_RR"]], -30, 30
    )

    keyboard.show()