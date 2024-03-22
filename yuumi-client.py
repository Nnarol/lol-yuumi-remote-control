#!/usr/bin/env python3

import sys
import requests
import threading
from pynput import mouse, keyboard
import time
import configparser

running = True

# Load configuration
config = configparser.ConfigParser()
config.read('config.ini')

yuumi_pc_ip = config.get('General', 'yuumi_server_ip')
server_port = config.get('General', 'yuumi_server_port')
click_url = f'http://{yuumi_pc_ip}:{server_port}/click'
keypress_url = f'http://{yuumi_pc_ip}:{server_port}/keypress'
key_release_url = f'http://{yuumi_pc_ip}:{server_port}/keyrelease'

MOUSE_TOGGLE_KEY = keyboard.Key[config.get('Keys', 'yuumi_enable_mouse_key')]
mouse_toggle_pressed = False

action_delay = 0.5
last_action_time = 0

try:
    print('Trying to connect...')
    requests.get(f'http://{yuumi_pc_ip}:{server_port}')
    print('Connected to Yuumi PC')
except requests.exceptions.ConnectionError:
    print('\033[91m' + 'Failed to connect to Yuumi PC. Please check the server IP and try running the script again.' + '\033[0m')
    sys.exit()

# Thie translation table is needed because pynput and the keyboard module
# name special keys differently.
# E.g. if the client detects and sends "cmd_l" (Left Windows Key), the server,
# which uses the keyboard module, won't know what "cmd_l" means,
# means, because keyboard calls it "left windows" rather than pynput's "cmd_l".
# Certain keys do not have a string representation at all in the keyboard
# module, such as Backspace or the arrow keys.
# Character keys are just represented by their characters in both modules.
special_keys_pynput_to_keyboard_repr = {
    "alt": "left alt",
    "alt_l": "left alt",
    "alt_r": "right alt",
    "alt_gr": "alt gr",
    "space": "space",
    "backspace": "space",
    "cmd_": "windows",
    "cmd_l": "left windows",
    "cmd_r": "right windows",
    "ctrl": "ctrl",
    "ctrl_l": "left ctrl",
    "ctrl_r": "right ctrl",
    "shift": "shift",
    "shift_l": "left shift",
    "shift_r": "right shift",
}

def key_is_allowed(key):
    return hasattr(key, "char") or key.name in special_keys_pynput_to_keyboard_repr

def send_request(url, json_data):
    try:
        requests.post(url, json=json_data, timeout=5.0)
    except requests.exceptions.Timeout:
        print("Request timed out")
    except Exception as e:
        print("Unhandled exception during request: {e}")

def key_pressed(key):
    global mouse_toggle_pressed

    if key_is_allowed(key):
        if key == MOUSE_TOGGLE_KEY:
            mouse_toggle_pressed = True
        send_key_event(key, keypress_url)
    else:
        print(f"Unallowed key: {key}")

def key_released(key):
    global mouse_toggle_pressed

    if key_is_allowed(key):
        if key == MOUSE_TOGGLE_KEY:
            mouse_toggle_pressed = False
        send_key_event(key, key_release_url)
    else:
        print(f"Unallowed key: {key}")

def send_key_event(key, url):
    if hasattr(key, "char"):
        data = {"action": key.char}
    else:
        data = {"action": special_keys_pynput_to_keyboard_repr[key.name]}
    send_request(url, data)

def on_click(x, y, button, pressed):
    global last_action_time, action_delay, last_action, mouse_toggle_pressed

    if mouse_toggle_pressed and not pressed:
        current_time = time.time()
        if current_time - last_action_time >= action_delay:
            print(f'{button.name} button clicked at ({x}, {y})')
            click_data = {'mouse_x': x, 'mouse_y': y, 'button': button.name}
            
            # Create and start a new thread for sending the request
            request_thread = threading.Thread(target=send_request, args=(click_url, click_data))
            request_thread.start()

            last_action_time = current_time
            last_action = None

mouse_listener = mouse.Listener(on_click=on_click, daemon=True)
mouse_listener.start()

hotkey_listener = keyboard.Listener(on_press=key_pressed, on_release=key_released, daemon=True)
hotkey_listener.start()

while running:
    time.sleep(1)
