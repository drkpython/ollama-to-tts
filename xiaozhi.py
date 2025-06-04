import asyncio
import websockets
import json
import sys
import speech_recognition as sr
import pyttsx3
import threading
import time
import platform
import subprocess
import re


class XiaozhiChat:
    def __init__(self):
        self.xiaozhi_api = "wss://api.xiaozhi.me/mcp/?token=eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOjM1Mjg5NiwiYWdlbnRJZCI6Mzg1OTc4LCJlbmRwb2ludElkIjoiYWdlbnRfMzg1OTc4IiwicHVycG9zZSI6Im1jcC1lbmRwb2ludCIsImlhdCI6MTc0OTAzMjg3MX0.AaUzVu4PdXfWUwi7M3BlVT-2skzzJ89YE9_8EVzqomx2bCYanTzeq-y0M4aD5V33yRHgXWFQhc6v5x-UR9b4LQ"  # 替换为你的小智 token
        self.setup_voice()
        self.message_id = 1  # 消息 ID 计数器

    def setup_voice(self):
        # 初始化语音引擎（与原代码一致）
        self.r = sr.Recognizer()
        self.engine = pyttsx3.init()
        self.set_audio_devices()
        self.engine.setProperty('rate', 250)
        self.engine.setProperty('volume', 1.0)
        self.engine._inLoop = False
        self.engine._driver = None

    # 以下设备设置方法（set_audio_devices/get_speakers等）与原代码完全一致，省略重复代码...

    async def send_message(self, prompt):
        """通过 WebSocket 发送消息到小智 API"""
        try:
            async with websockets.connect(self.xiaozhi_api) as websocket:
                # 构造小智 API 所需的消息格式
                message = {
                    "type": "text",
                    "content": prompt,
                    "messageId": str(self.message_id),
                    "timestamp": int(time.time() * 1000),
                    # 从 token 中获取的用户信息（需与你的 token 匹配）
                    "userId": 352896,  
                    "agentId": 395978,  
                    "sessionId": f"session_{int(time.time())}"
                }
                await websocket.send(json.dumps(message))
                
                # 接收流式回复
                response = ""
                async for msg in websocket:
                    try:
                        data = json.loads(msg)
                        if data.get("type") == "text":
                            response += data.get("content", "")
                            print(data.get("content", ""), end="", flush=True)
                    except json.JSONDecodeError:
                        continue
                return response

        except websockets.exceptions.ConnectionClosedError as e:
            print(f"\n连接错误: {e}")
            return None
        except Exception as e:
            print(f"\n发送消息失败: {e}")
            return None

    def recognize_speech(self):
        """语音识别（与原代码一致）"""
        with self.microphone as source:
            print("\n请说话，正在聆听...", end='', flush=True)
            self.r.adjust_for_ambient_noise(source, duration=0.5)
            audio = self.r.listen(source, timeout=10, phrase_time_limit=60)

        try:
            text = self.r.recognize_google(audio, language='cmn-Hans-CN')
            print(f"你说: {text}")
            return text
        except Exception as e:
            print(f"语音识别失败: {e}")
            return None

    def speak(self, text):
        """语音合成（与原代码一致）"""
        if not text:
            return
        threading.Thread(target=self._speak_thread, args=(text,)).start()

    async def run_chat(self):
        print("\n=== 小智语音对话机器人 ===")
        print("输入'exit'退出，输入'voice'启用语音交互，输入'text'返回文本交互")
        print("输入'change device'更改麦克风或扬声器设置\n")

        input_mode = 'text'
        while True:
            try:
                if input_mode == 'voice':
                    prompt = self.recognize_speech()
                    if not prompt:
                        continue
                else:
                    prompt = input("你: ").strip()

                # 处理控制命令（与原代码一致）
                if prompt.lower() == 'exit':
                    print("\n=== 对话已结束 ===")
                    break
                elif prompt.lower() in ['voice', 'text', 'change device']:
                    # 调用原有逻辑
                    if prompt.lower() == 'voice':
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

                # 发送消息到小智 API
                print("\n小智: ", end='', flush=True)
                response = await self.send_message(prompt)
                self.message_id += 1  # 递增消息 ID

                if response:
                    print("\n")  # 换行
                    self.speak(response)  # 语音播报回复

            except KeyboardInterrupt:
                print("\n=== 对话已终止 ===")
                sys.exit(0)
            except Exception as e:
                print(f"\n发生错误: {str(e)}")


if __name__ == "__main__":
    chat = XiaozhiChat()
    asyncio.run(chat.run_chat())
