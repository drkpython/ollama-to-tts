import requests
import json
import sys
import speech_recognition as sr
import pyttsx3
import threading
import time
import platform
import subprocess
import re


class OllamaChat:
    def __init__(self):
        self.ollama_host = self.get_host()
        self.model_name = self.get_model()
        self.setup_voice()

    def setup_voice(self):
        # 初始化语音引擎
        self.r = sr.Recognizer()
        self.engine = pyttsx3.init()

        # 设置中文语音引擎和输入/输出设备
        self.set_audio_devices()

        # 设置语速和音量
        self.engine.setProperty('rate', 250)  # 语速
        self.engine.setProperty('volume', 1.0)  # 音量

        # 解决run loop already started错误
        self.engine._inLoop = False
        self.engine._driver = None

    def set_audio_devices(self):
        """设置语音引擎、麦克风和扬声器"""
        # 选择麦克风
        print("\n可用麦克风列表:")
        mic_list = sr.Microphone.list_microphone_names()
        for i, mic_name in enumerate(mic_list):
            print(f"{i}. {mic_name}")

        while True:
            try:
                mic_idx = int(input("请选择麦克风编号 (默认0): ") or "0")
                if 0 <= mic_idx < len(mic_list):
                    self.microphone = sr.Microphone(device_index=mic_idx)
                    print(f"已选择麦克风: {mic_list[mic_idx]}")
                    break
                else:
                    print("编号无效，请重新输入")
            except ValueError:
                print("请输入有效的数字")

        # 选择扬声器
        speakers = self.get_speakers()
        if speakers:
            print("\n可用扬声器列表:")
            for i, speaker in enumerate(speakers):
                print(f"{i}. {speaker}")

            while True:
                try:
                    speaker_idx = int(input("请选择扬声器编号 (默认0): ") or "0")
                    if 0 <= speaker_idx < len(speakers):
                        self.selected_speaker = speakers[speaker_idx]
                        print(f"已选择扬声器: {self.selected_speaker}")

                        # 尝试设置默认扬声器
                        success = self.set_default_speaker(speaker_idx)
                        if not success:
                            print("\n警告: 无法自动设置默认扬声器。")
                            print("请通过系统音频设置手动选择扬声器:")
                            self.show_audio_settings_instructions()
                        break
                    else:
                        print("编号无效，请重新输入")
                except ValueError:
                    print("请输入有效的数字")
        else:
            print("\n无法获取扬声器列表，将使用系统默认设置")
            self.selected_speaker = "系统默认"
            self.show_audio_settings_instructions()

        # 选择语音引擎
        print("\n可用语音列表:")
        voices = self.engine.getProperty('voices')
        chinese_voices = []
        other_voices = []

        for voice in voices:
            if 'chinese' in voice.id.lower() or 'china' in voice.id.lower():
                chinese_voices.append(voice)
            else:
                other_voices.append(voice)

        # 优先显示中文语音
        display_voices = chinese_voices + other_voices
        for i, voice in enumerate(display_voices):
            print(f"{i}. {voice.name} ({voice.id})")

        while True:
            try:
                voice_idx = int(input("请选择语音编号 (默认第一个中文语音或0): ") or
                                (0 if not chinese_voices else chinese_voices[0].id))
                if 0 <= voice_idx < len(display_voices):
                    self.engine.setProperty('voice', display_voices[voice_idx].id)
                    print(f"已选择语音: {display_voices[voice_idx].name}")
                    break
                else:
                    print("编号无效，请重新输入")
            except ValueError:
                print("请输入有效的数字")

    def get_speakers(self):
        """根据不同操作系统获取扬声器列表"""
        current_os = platform.system()
        speakers = []

        if current_os == "Windows":
            try:
                # 尝试使用WMIC获取音频设备
                result = subprocess.run(
                    ["wmic", "PATH", "Win32_SoundDevice", "GET", "Name"],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    # 解析输出
                    for line in result.stdout.split('\n'):
                        line = line.strip()
                        if line and not line.startswith("Name"):
                            speakers.append(line)
            except Exception as e:
                print(f"获取扬声器列表失败: {e}")
                # 回退方案
                speakers = ["默认扬声器", "耳机", "外部扬声器"]

        elif current_os == "Linux":
            try:
                # 尝试使用pactl (PulseAudio)
                result = subprocess.run(
                    ["pactl", "list", "sinks"],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    # 使用正则表达式提取设备名称
                    pattern = re.compile(r'Name: ([^\n]+)\n\s+Description: ([^\n]+)')
                    for match in pattern.finditer(result.stdout):
                        speakers.append(f"{match.group(2)} ({match.group(1)})")
            except Exception:
                try:
                    # 尝试使用aplay
                    result = subprocess.run(
                        ["aplay", "-L"],
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        # 提取设备名称
                        for line in result.stdout.split('\n'):
                            if line.startswith("hw:"):
                                speakers.append(line.strip())
                except Exception as e:
                    print(f"获取扬声器列表失败: {e}")
                    speakers = ["默认输出"]

        elif current_os == "Darwin":  # macOS
            try:
                # 使用osascript获取音频设备
                script = """
                tell application "System Events"
                    set outputDevices to name of every audio output device
                end tell
                return outputDevices
                """
                result = subprocess.run(
                    ["osascript", "-e", script],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    # 解析输出
                    output = result.stdout.strip()
                    if output.startswith("{") and output.endswith("}"):
                        output = output[1:-1]
                        devices = [device.strip().strip('"') for device in output.split(',')]
                        speakers = [device for device in devices if device]
            except Exception as e:
                print(f"获取扬声器列表失败: {e}")
                speakers = ["内置扬声器", "耳机"]

        return speakers

    def set_default_speaker(self, speaker_idx):
        """设置默认扬声器（特定于操作系统的实现）"""
        current_os = platform.system()

        if current_os == "Windows":
            try:
                # 尝试使用nircmd (如果安装)
                subprocess.run(
                    [r"nircmd.exe", "setdefaultsounddevice", str(speaker_idx)],
                    capture_output=True,
                    check=True
                )
                return True
            except Exception:
                print("\n提示: 要支持自动设置默认扬声器，请安装nircmd工具并确保在PATH环境变量中")
                print("下载地址: https://www.nirsoft.net/utils/nircmd.html")
                return False

        elif current_os == "Linux":
            try:
                # 使用pactl设置默认输出
                speakers = self.get_speakers()
                if speaker_idx < len(speakers):
                    # 提取设备名称
                    device_name = speakers[speaker_idx].split('(')[-1].replace(')', '').strip()
                    subprocess.run(
                        ["pactl", "set-default-sink", device_name],
                        capture_output=True,
                        check=True
                    )
                    return True
            except Exception:
                return False

        elif current_os == "Darwin":  # macOS
            try:
                # 使用SwitchAudioSource工具
                speakers = self.get_speakers()
                if speaker_idx < len(speakers):
                    device_name = speakers[speaker_idx]
                    subprocess.run(
                        ["SwitchAudioSource", "-s", device_name],
                        capture_output=True,
                        check=True
                    )
                    return True
            except Exception:
                print("\n提示: 要支持自动设置默认扬声器，请安装SwitchAudioSource工具")
                print("安装命令: brew install switchaudio-osx")
                return False

        return False

    def show_audio_settings_instructions(self):
        """显示如何手动更改系统音频设置的说明"""
        current_os = platform.system()

        if current_os == "Windows":
            print("- Windows: 右键点击任务栏音量图标 > 选择播放设备 > 选择所需扬声器")
        elif current_os == "Linux":
            print("- Linux: 使用系统设置应用或pavucontrol工具更改默认输出设备")
        elif current_os == "Darwin":
            print("- macOS: 点击菜单栏音量图标 > 选择所需扬声器")

    def get_host(self):
        while True:
            host = input("请输入Ollama服务器地址（https://freeollama.oneplus1.top/）111.200.200.217:11434: ").strip()
            if not host.startswith(('http://', 'https://')):
                host = 'http://' + host
            try:
                requests.head(host, timeout=5)
                return host
            except requests.exceptions.RequestException as e:
                print(f"地址无效: {str(e)}，请重新输入")

    def get_model(self):
        while True:
            model = input("请输入模型名称driaforall/tiny-agent-a:0.5b: ").strip()
            if model:
                return model
            else:
                print("模型名称不能为空，请重新输入")

    def send_request(self, prompt):
        try:
            response = requests.post(
                f"{self.ollama_host}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": True
                },
                stream=True,
                timeout=60  # 增加超时时间
            )
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            print(f"请求失败: {str(e)}")
            return None

    def recognize_speech(self):
        """语音识别函数，返回识别的文本"""
        with self.microphone as source:
            print("\n请说话，正在聆听...", end='', flush=True)
            self.r.adjust_for_ambient_noise(source, duration=0.5)  # 环境降噪
            audio = self.r.listen(source, timeout=10, phrase_time_limit=60)  # 10秒超时，30秒最长语音

        try:
            print("正在识别...", end='', flush=True)
            text = self.r.recognize_google(audio, language='cmn-Hans-CN')  # 使用Google语音识别
            print(f"你说: {text}")
            return text
        except sr.UnknownValueError:
            print("无法识别语音")
            return None
        except sr.RequestError as e:
            print(f"请求错误; {e}")
            return None
        except sr.WaitTimeoutError:
            print("聆听超时")
            return None

    def speak(self, text):
        """语音合成函数，将文本转换为语音输出"""
        # 如果文本为空则直接返回
        if not text or text.strip() == "":
            return

        # 在单独线程中进行语音合成，避免阻塞主线程
        threading.Thread(target=self._speak_thread, args=(text,)).start()

    def _speak_thread(self, text):
        try:
            # 确保引擎状态正常
            if self.engine._inLoop:
                self.engine.endLoop()
                self.engine._inLoop = False

            self.engine.say(text)
            self.engine.runAndWait()
        except Exception as e:
            print(f"语音合成错误: {e}")

    def run_chat(self):
        print("\n=== 多轮对话已启动 ===")
        print("输入'exit'退出，输入'voice'启用语音交互，输入'text'返回文本交互")
        print("输入'change device'更改麦克风或扬声器设置\n")

        input_mode = 'text'  # 默认文本模式

        while True:
            try:
                # 根据当前模式获取输入
                if input_mode == 'voice':
                    prompt = self.recognize_speech()
                    if not prompt:
                        continue
                else:
                    prompt = input("你: ").strip()

                # 处理控制命令
                if prompt.lower() == 'exit':
                    print("\n=== 对话已结束 ===")
                    break
                elif prompt.lower() == 'voice':
                    input_mode = 'voice'
                    print("=== 已切换到语音输入模式 ===")
                    continue
                elif prompt.lower() == 'text':
                    input_mode = 'text'
                    print("=== 已切换到文本输入模式 ===")
                    continue
                elif prompt.lower() == 'change device':
                    self.set_audio_devices()
                    continue

                # 发送请求
                response = self.send_request(prompt)
                if not response:
                    continue

                # 处理流式响应
                print("\nAI: ", end='', flush=True)
                full_response = ""
                for line in response.iter_lines():
                    if line:
                        try:
                            chunk = line.decode('utf-8')
                            data = json.loads(chunk)
                            chunk_text = data.get("response", "")
                            print(chunk_text, end='', flush=True)
                            full_response += chunk_text
                        except json.JSONDecodeError:
                            continue
                print("\n")  # 回车换行

                # 语音输出完整响应
                self.speak(full_response)

            except KeyboardInterrupt:
                print("\n=== 对话已终止 ===")
                sys.exit(0)
            except Exception as e:
                print(f"发生错误: {str(e)}\n")


if __name__ == "__main__":
    chat = OllamaChat()
    chat.run_chat()
