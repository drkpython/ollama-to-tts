import json
import time
import threading
import pyaudio
import opuslib
import socket
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import logging
import RPi.GPIO as GPIO
import os
import errno

# 设置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='app.log',
    filemode='w'
)

# ============ GPIO配置 ==============
BUTTON_PIN = 16
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# ============ 全局变量 ==============
aes_opus_info = {
    "session_id": "b23ebfe9",
    "udp": {
        "server": "120.24.160.13",
        "port": 8884,
        "encryption": "aes-128-ctr",
        "key": "263094c3aa28cb42f3965a1020cb21a7",
        "nonce": "01000000ccba9720b4bc268100000000"
    },
    "audio_params": {
        "format": "opus",
        "sample_rate": 24000,
        "channels": 1,
        "frame_duration": 60
    }
}

local_sequence = 0
listen_state = None
key_state = None
audio = None
udp_socket = None
running = True

# 线程管理
recv_audio_thread = None
send_audio_thread = None

# ============ 核心功能 ==============
def aes_ctr_encrypt(key, nonce, plaintext):
    cipher = Cipher(algorithms.AES(key), modes.CTR(nonce), backend=default_backend())
    encryptor = cipher.encryptor()
    return encryptor.update(plaintext) + encryptor.finalize()

def aes_ctr_decrypt(key, nonce, ciphertext):
    cipher = Cipher(algorithms.AES(key), modes.CTR(nonce), backend=default_backend())
    decryptor = cipher.decryptor()
    plaintext = decryptor.update(ciphertext) + decryptor.finalize()
    return plaintext

def send_audio():
    global aes_opus_info, udp_socket, local_sequence, listen_state, audio, running
    key = aes_opus_info['udp']['key']
    nonce = aes_opus_info['udp']['nonce']
    server_ip = aes_opus_info['udp']['server']
    server_port = aes_opus_info['udp']['port']

    encoder = opuslib.Encoder(16000, 1, opuslib.APPLICATION_AUDIO)
    mic = audio.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=960)

    try:
        while running and aes_opus_info['session_id']:
            if listen_state == "stop":
                time.sleep(0.1)
                continue

            data = mic.read(960)
            encoded_data = encoder.encode(data, 960)

            local_sequence += 1
            new_nonce = nonce[0:4] + format(len(encoded_data), '04x') + nonce[8:24] + format(local_sequence, '08x')

            encrypt_encoded_data = aes_ctr_encrypt(
                bytes.fromhex(key),
                bytes.fromhex(new_nonce),
                bytes(encoded_data)
            )
            data = bytes.fromhex(new_nonce) + encrypt_encoded_data
            try:
                udp_socket.sendto(data, (server_ip, server_port))
            except socket.error as e:
                if e.errno == errno.ENETUNREACH:
                    restart_audio_streams()
                    break
                else:
                    raise
    except Exception as e:
        logging.error(f"音频发送错误: {str(e)}")
    finally:
        mic.stop_stream()
        mic.close()

def recv_audio():
    global aes_opus_info, udp_socket, audio, running
    key = aes_opus_info['udp']['key']
    sample_rate = aes_opus_info['audio_params']['sample_rate']
    frame_duration = aes_opus_info['audio_params']['frame_duration']
    frame_num = int(frame_duration / (1000 / sample_rate))

    decoder = opuslib.Decoder(sample_rate, 1)
    spk = audio.open(format=pyaudio.paInt16, channels=1, rate=sample_rate, output=True, frames_per_buffer=frame_num)

    try:
        while running and aes_opus_info['session_id']:
            try:
                data, server = udp_socket.recvfrom(4096)
                split_nonce = data[:16]
                encrypt_data = data[16:]

                decrypt_data = aes_ctr_decrypt(
                    bytes.fromhex(key),
                    split_nonce,
                    encrypt_data
                )
                spk.write(decoder.decode(decrypt_data, frame_num))
            except socket.timeout:
                continue
            except Exception as e:
                logging.error(f"音频接收错误: {str(e)}")
    finally:
        spk.stop_stream()
        spk.close()

def restart_audio_streams():
    global aes_opus_info, recv_audio_thread, send_audio_thread, udp_socket

    if udp_socket:
        udp_socket.close()
    if recv_audio_thread and recv_audio_thread.is_alive():
        recv_audio_thread.join()
    if send_audio_thread and send_audio_thread.is_alive():
        send_audio_thread.join()

    try:
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.settimeout(1)
        udp_socket.connect((aes_opus_info['udp']['server'], aes_opus_info['udp']['port']))

        recv_audio_thread = threading.Thread(target=recv_audio, daemon=True)
        recv_audio_thread.start()
        send_audio_thread = threading.Thread(target=send_audio, daemon=True)
        send_audio_thread.start()
    except Exception as e:
        logging.error(f"UDP连接失败: {str(e)}")

def on_space_key_press(event=None):
    global key_state, listen_state
    key_state = "press"
    print("倾听中...")
    listen_state = "start"

def on_space_key_release(event=None):
    global key_state, listen_state
    key_state = "release"
    print("停止倾听")
    listen_state = "stop"

def button_pressed_callback(channel):
    if GPIO.input(BUTTON_PIN) == GPIO.LOW:  # 按钮按下
        on_space_key_press()
    else:  # 按钮释放
        on_space_key_release()

def run():
    global audio, running
    try:
        audio = pyaudio.PyAudio()

        print("程序启动")
        logging.info("程序启动")
        
        # 初始化UDP连接
        restart_audio_streams()

        # 设置GPIO事件检测
        GPIO.add_event_detect(BUTTON_PIN, GPIO.BOTH, callback=button_pressed_callback, bouncetime=50)

        print("按空格键开始录音，松开停止")
        print("按 Ctrl+C 退出程序")
        
        # 等待用户输入
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n程序已停止")
        
    except Exception as e:
        print(f"运行时错误: {str(e)}")
        logging.error(f"运行时错误: {str(e)}")
    finally:
        GPIO.cleanup()
        if udp_socket:
            udp_socket.close()
        if audio:
            audio.terminate()
        logging.info("资源清理完成")

if __name__ == "__main__":
    run()
