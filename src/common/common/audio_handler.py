"""
音频处理器
离线TTS + 强制输出到 Y11 USB 扬声器
无需联网，不使用 gTTS
"""
import os
import subprocess
from typing import Optional

# 导入日志
from .logger_config import get_logger
logger = get_logger(__name__)


class AudioHandler:
    def __init__(self):
        # 自动获取 Y11 声卡卡号（hw:X 中的 X）
        self.y11_card = self._get_y11_card_number()
        if self.y11_card is not None:
            logger.info(f"✅ 找到 Y11 扬声器，声卡卡号: card={self.y11_card}")
        else:
            logger.error("❌ 未找到 Y11 USB 音频设备")

    def _get_y11_card_number(self):
        """获取 Y11 对应的 ALSA 声卡编号"""
        try:
            result = subprocess.run(
                ["cat", "/proc/asound/cards"],
                capture_output=True, text=True
            )
            for line in result.stdout.splitlines():
                if "Y11" in line:
                    card_num = line.strip().split()[0]
                    return card_num
            return None
        except:
            return None

    def play_with_external_speaker(self, text: str) -> bool:
        if self.y11_card is None:
            logger.error("❌ 无 Y11 设备")
            return False

        try:
            import uuid
            wav_file = f"/tmp/tts_{uuid.uuid4().hex}.wav"

            logger.info(f"🔊 播放: {text}")
            logger.info(f"Using device: plughw:{self.y11_card},0")

            # ✅ ① 用英文语音（指定 en-us，避免乱读）
            subprocess.run([
                "espeak",
                "-v", "en-us",  # ⭐ 关键：指定英文
                "-s", "150",  # 语速（可调）
                text,
                "-w", wav_file
            ], check=True)

            # ✅ ② 播放（plughw，已验证正确）
            subprocess.run([
                "aplay",
                "-D", f"plughw:{self.y11_card},0",
                wav_file
            ], check=True)

            # ✅ ③ 删除临时文件
            os.remove(wav_file)

            logger.info("✅ 播放完成")
            return True

        except Exception as e:
            logger.error(f"播放失败: {e}")
            return False


if __name__ == "__main__":
    audio = AudioHandler()
    audio.play_with_external_speaker("Hello Nathan, this is Y11 speaker speaking.")