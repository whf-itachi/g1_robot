import time
import threading
from unitree_sdk2py.g1.loco.g1_loco_client import LocoClient


class MotionController:
    """
    G1 机器人运动控制器
    
    状态机:
        IDLE     - 空闲状态，可接受新指令
        GREETING - 正在执行问候动作
        STOPPING - 正在停止
        MOVING   - 正在移动
    """

    def __init__(self):
        self.motion = LocoClient()
        self.motion.Init()
        self.motion.WaitLeaseApplied()
        self.motion.Start()
        self.motion.HighStand()
        
        self._state = "IDLE"
        self._lock = threading.Lock()

    def _set_state(self, new_state):
        """线程安全的状态设置（内部使用）"""
        with self._lock:
            self._state = new_state

    def _get_state(self):
        """线程安全的状态获取"""
        with self._lock:
            return self._state

    def stop(self):
        """停止机器人当前动作"""
        if self._get_state() == "STOPPING":
            return
        
        self._set_state("STOPPING")
        self.motion.StopMove()
        self._set_state("IDLE")

    def wave_hand(self):
        """执行挥手/握手动作"""
        current_state = self._get_state()
        if current_state == "GREETING":
            return
        if current_state in ["STOPPING", "MOVING"]:
            self.stop()
        
        self._set_state("GREETING")
        self.motion.ShakeHand()
        time.sleep(1.0)
        self.motion.HighStand()
        self._set_state("IDLE")

    def is_moving(self):
        """判断机器人是否正在移动"""
        return self._get_state() == "MOVING"

    def is_busy(self):
        """判断机器人是否忙碌（不可接受新指令）"""
        return self._get_state() in ["STOPPING", "GREETING", "MOVING"]
