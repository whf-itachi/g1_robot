"""
语音处理模块
提供语音输入和语音输出功能
"""
import os
import json
import threading
from typing import Optional, Callable
import queue

# 导入日志配置
from .logger_config import get_logger

# 创建模块级日志记录器
logger = get_logger(__name__)

# 尝试导入所需的库
try:
    import sounddevice as sd
    import numpy as np
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False
    logger.warning("Warning: sounddevice not installed. Install with: pip install sounddevice")

try:
    from vosk import Model, KaldiRecognizer
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False
    logger.warning("Warning: vosk not installed. Install with: pip install vosk")

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False
    logger.warning("Warning: pyttsx3 not installed. Install with: pip install pyttsx3")


class AudioHandler:
    def __init__(self, model_path: str = "model", sample_rate: int = 16000):
        self.model_path = model_path
        self.sample_rate = sample_rate
        self.channels = 1
        self.block_size = 8000

        # 音频设备ID
        self.input_device_id: Optional[int] = None
        self.output_device_id: Optional[int] = None

        # 语音识别相关
        self.recognizer = None
        self.model = None

        # 文本转语音引擎
        self.tts_engine = None
        self.tts_lock = threading.Lock()

        # 录音相关
        self.is_listening = False
        self.audio_queue = queue.Queue()

        # 回调函数
        self.on_speech_recognized: Optional[Callable[[str], None]] = None

        # 日志配置
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")

        # 初始化
        self._init_tts_engine()
        self._find_best_devices()

    def _init_tts_engine(self):
        """初始化文本转语音引擎"""
        if PYTTSX3_AVAILABLE:
            try:
                self.tts_engine = pyttsx3.init()

                # Linux系统配置
                self.tts_engine.setProperty('rate', 150)  # 语速
                self.tts_engine.setProperty('volume', 0.5)  # 音量

                self.logger.info("Text-to-speech engine initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize TTS engine: {e}")
        else:
            self.logger.warning("Pyttsx3 not available, TTS functionality disabled")

    def _find_best_devices(self):
        """查找最佳输入和输出设备"""
        if not SOUNDDEVICE_AVAILABLE:
            self.logger.error("SoundDevice not available, cannot find audio devices")
            return

        try:
            devices = sd.query_devices()

            # 查找Y11设备（优先匹配Y11 USB Audio设备）
            y11_input_id = None
            y11_output_id = None

            for idx, device in enumerate(devices):
                # 匹配特征：名称含 Y11
                if "Y11" in device['name']:
                    if device['max_input_channels'] > 0:
                        y11_input_id = idx
                    if device['max_output_channels'] > 0:
                        y11_output_id = idx

            # 如果找到Y11设备，优先使用
            if y11_input_id is not None:
                self.input_device_id = y11_input_id
                device_info = devices[y11_input_id]
                self.logger.info(f"Selected Y11 input device: [{y11_input_id}] {device_info['name']}")
            else:
                # 查找其他输入设备（麦克风）
                for idx, device in enumerate(devices):
                    if device['max_input_channels'] > 0:
                        # 优先选择包含麦克风关键词的设备
                        name_upper = device['name'].upper()
                        if any(keyword in name_upper for keyword in ['MIC', 'MICROPHONE']):
                            self.input_device_id = idx
                            self.logger.info(f"Selected input device: [{idx}] {device['name']}")
                            break
                else:
                    # 如果没找到特定设备，使用默认输入设备
                    default_input = sd.default.device[0]
                    if default_input is not None:
                        self.input_device_id = default_input
                        device_info = devices[default_input]
                        self.logger.info(f"Using default input device: [{default_input}] {device_info['name']}")

            # 为输出设备同样优先考虑Y11
            if y11_output_id is not None:
                self.output_device_id = y11_output_id
                device_info = devices[y11_output_id]
                self.logger.info(f"Selected Y11 output device: [{y11_output_id}] {device_info['name']}")
            else:
                # 查找其他输出设备（扬声器）
                for idx, device in enumerate(devices):
                    if device['max_output_channels'] > 0:
                        # 优先选择包含扬声器关键词的设备
                        name_upper = device['name'].upper()
                        if any(keyword in name_upper for keyword in ['SPEAKER', 'HEADPHONE', 'HEADSET']):
                            self.output_device_id = idx
                            self.logger.info(f"Selected output device: [{idx}] {device['name']}")
                            break
                else:
                    # 如果没找到特定设备，使用默认输出设备
                    default_output = sd.default.device[1]
                    if default_output is not None:
                        self.output_device_id = default_output
                        device_info = devices[default_output]
                        self.logger.info(f"Using default output device: [{default_output}] {device_info['name']}")

        except Exception as e:
            self.logger.error(f"Error finding audio devices: {e}")

    def speak_text(self, text: str, blocking: bool = True):
        """
        播放文本语音
        
        Args:
            text: 要播放的文本
            blocking: 是否阻塞直到播放完成
        """
        if not self.tts_engine:
            self.logger.error("TTS engine not available")
            return False
            
        try:
            with self.tts_lock:
                self.tts_engine.say(text)
                if blocking:
                    self.tts_engine.runAndWait()
                else:
                    # 在后台线程中运行，避免阻塞主线程
                    def run_tts():
                        self.tts_engine.runAndWait()
                    
                    tts_thread = threading.Thread(target=run_tts, daemon=True)
                    tts_thread.start()
                    
            self.logger.info(f"Spoken: {text}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error speaking text: {e}")
            return False

    def preload_vosk_model(self):
        """预加载Vosk语音识别模型"""
        if not VOSK_AVAILABLE:
            self.logger.error("Vosk not available, cannot load model")
            return False
            
        if not os.path.exists(self.model_path):
            self.logger.error(f"Vosk model not found at: {self.model_path}")
            return False
            
        try:
            self.model = Model(self.model_path)
            self.recognizer = KaldiRecognizer(self.model, self.sample_rate)
            self.recognizer.SetPartialWords(True)
            self.logger.info("Vosk model loaded successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error loading Vosk model: {e}")
            return False

    def start_listening(self, callback: Optional[Callable[[str], None]] = None):
        """
        开始监听语音输入
        
        Args:
            callback: 语音识别后的回调函数
        """
        if not SOUNDDEVICE_AVAILABLE:
            self.logger.error("SoundDevice not available, cannot start listening")
            return False
            
        if not self.input_device_id:
            self.logger.error("No input device available")
            return False
            
        if callback:
            self.on_speech_recognized = callback
            
        if not self.model or not self.recognizer:
            if not self.preload_vosk_model():
                self.logger.error("Cannot start listening without Vosk model")
                return False
        
        self.is_listening = True
        
        def audio_callback(indata, frames, time_info, status):
            if status:
                self.logger.warning(f"Audio status: {status}")
            self.audio_queue.put(bytes(indata))

        def listen_worker():
            try:
                with sd.RawInputStream(
                        device=self.input_device_id,
                        samplerate=self.sample_rate,
                        blocksize=self.block_size,
                        dtype='int16',
                        channels=self.channels,
                        callback=audio_callback
                ):
                    while self.is_listening:
                        data = self.audio_queue.get()
                        
                        if self.recognizer.AcceptWaveform(data):
                            result = json.loads(self.recognizer.Result())
                            text = result.get("text", "").strip()
                            if text:
                                self.logger.info(f"Recognized: {text}")
                                
                                # 调用回调函数
                                if self.on_speech_recognized:
                                    try:
                                        self.on_speech_recognized(text)
                                    except Exception as e:
                                        self.logger.error(f"Error in speech recognition callback: {e}")
                        else:
                            # 可选：处理部分识别结果
                            partial = json.loads(self.recognizer.PartialResult())
                            partial_text = partial.get("partial", "").strip()
                            if partial_text:
                                self.logger.info(f"Listening: {partial_text}")
            except Exception as e:
                self.logger.error(f"Error in audio listening: {e}")
                self.is_listening = False

        # 在后台线程中启动监听
        listen_thread = threading.Thread(target=listen_worker, daemon=True)
        listen_thread.start()
        
        self.logger.info("Started listening for speech input")
        return True

    def recognize_speech_once(self, timeout: int = 10) -> Optional[str]:
        """
        单次语音识别，等待用户说出一句话
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            识别到的文本，如果超时或出错则返回None
        """
        if not SOUNDDEVICE_AVAILABLE:
            self.logger.error("SoundDevice not available, cannot recognize speech")
            return None
            
        if not self.input_device_id:
            self.logger.error("No input device available")
            return None
            
        if not self.model or not self.recognizer:
            if not self.preload_vosk_model():
                self.logger.error("Cannot recognize speech without Vosk model")
                return None

        result_text = None
        got_result = threading.Event()

        def audio_callback(indata, frames, time_info, status):
            if status:
                self.logger.warning(f"Audio status: {status}")
            self.audio_queue.put(bytes(indata))

        def recognize_worker():
            nonlocal result_text
            try:
                with sd.RawInputStream(
                        device=self.input_device_id,
                        samplerate=self.sample_rate,
                        blocksize=self.block_size,
                        dtype='int16',
                        channels=self.channels,
                        callback=audio_callback
                ):
                    while not got_result.is_set():
                        try:
                            data = self.audio_queue.get(timeout=0.1)
                            
                            if self.recognizer.AcceptWaveform(data):
                                result = json.loads(self.recognizer.Result())
                                text = result.get("text", "").strip()
                                if text:
                                    result_text = text
                                    self.logger.info(f"Recognized: {text}")
                                    got_result.set()
                                    break
                        except queue.Empty:
                            continue
            except Exception as e:
                self.logger.error(f"Error in single speech recognition: {e}")
                got_result.set()

        # 在后台线程中运行识别
        recognize_thread = threading.Thread(target=recognize_worker, daemon=True)
        recognize_thread.start()
        
        # 等待结果或超时
        got_result.wait(timeout=timeout)
        
        if not got_result.is_set():
            self.logger.info("Speech recognition timed out")
            return None
        
        return result_text

    def stop_listening(self):
        """停止监听语音输入"""
        self.is_listening = False
        self.logger.info("Stopped listening for speech input")

    def set_y11_volume(self):
        """自动调整 Y11 设备（hw:2,0 对应 card 2）的音量"""
        try:
            import subprocess
            # 调整 PCM 音量（Y11 设备只有 PCM 控件）
            subprocess.run(
                ["amixer", "-c", "2", "set", "PCM", "unmute", "50%"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self.logger.info("Y11 speaker volume adjusted to 50% (unmuted)")
            return True
        except Exception as e:
            self.logger.warning(f"Volume adjustment failed (won't affect playback): {e}")
            return False

    def set_y11_volume(self):
        """自动调整 Y11 设备（hw:2,0 对应 card 2）的音量"""
        try:
            import subprocess
            # 调整 PCM 音量（Y11 设备只有 PCM 控件）
            subprocess.run(
                ["amixer", "-c", "2", "set", "PCM", "unmute", "50%"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self.logger.info("Y11 speaker volume adjusted to 50% (unmuted)")
            return True
        except Exception as e:
            self.logger.warning(f"Volume adjustment failed (won't affect playback): {e}")
            return False

# 全局音频处理器实例
audio_handler = None


def get_audio_handler(model_path: str = "model", sample_rate: int = 16000) -> Optional[AudioHandler]:
    """
    获取全局音频处理器实例

    Args:
        model_path: Vosk模型路径
        sample_rate: 采样率

    Returns:
        AudioHandler实例或None
    """
    global audio_handler
    if audio_handler is None:
        try:
            audio_handler = AudioHandler(model_path, sample_rate)
        except Exception as e:
            logger = get_logger(__name__)
            logger.error(f"Failed to create audio handler: {e}")
            return None
    return audio_handler