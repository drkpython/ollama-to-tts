# ollama-to-tts
K博士开发

警告，未经授权接入api可能会带来法律责任，请自行斟酌，本代码只供学习之用！！！

这是一个基于python的嵌入式llm对话项目（兼容树莓派）（还未调试！）/Here is a Python-based embedded LLM conversation code (compatible with Raspberry Pi)(NOT YET!).

从https://freeollama.oneplus1.top/
上找来的api和模型名称直接按照我的脚本提示往里面复制就可以

注意，在中国境内使用需要开启vpn，因为google的语音识别转文字api在大陆不能用。

本程序的llm api接入和语音识别api接入完全免费，不需要任何sdk，只要你有网络就能使用。

The API and model names obtained from https://freeollama.oneplus1.top/ can be directly copied into the script as prompted.

Warning: Unauthorized access to the API may result in legal consequences. Please exercise your own judgment. This code is provided solely for learning purposes!!!

Note that in mainland China, you need to turn on a VPN because Google's speech recognition and text conversion API is not available in the region.

The LLM API and speech recognition API access for this program are completely free. No SDK is required. You can use it as long as you have an internet connection.

# 白嫖Ollama
## 特性亮点 ✨
- 🎙️ **双模态交互**：支持语音输入/输出和纯文本模式无缝切换
- 🌐 **跨平台支持**：Windows/macOS/Linux全平台兼容
- 🎛️ **智能设备管理**：自动检测+手动配置音频设备
- 🚀 **流式响应**：实时显示模型生成内容
- 🔒 **安全通信**：HTTPS连接+SSL证书验证

## Win如果用Pycharm直接拉仓库🚀python3.9.2

```bash
#拉仓库依赖自动装
git clone https://github.com/drkpython/ollama-to-tts.git
```
## ‌raspberry‌ Pi调试中（即将更新）
```bash
```
```bash
# 创建虚拟环境（macOS/Linux）
python3 -m venv venv
```

```bash
#装依赖
pip install -r requirements.txt
```
```bash
#这是用到的库
certifi==2025.1.31
charset-normalizer==3.4.1
idna==3.10
importlib_metadata==8.6.1
packaging==24.2
PyAudio==0.2.14
pycparser==2.22
pyttsx3==2.98
pywin32==310
requests==2.32.3
SpeechRecognition==3.14.3
urllib3==2.3.0
```
