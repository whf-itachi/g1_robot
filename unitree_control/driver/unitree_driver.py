"""
unitree_driver.py
稳定版底层控制器（支持关节控制）
"""

import threading
import logging
import time

from unitree_sdk2py.core.channel import (
    ChannelFactoryInitialize,
    ChannelPublisher,
    ChannelSubscriber,
)

from unitree_sdk2py.g1.loco.g1_loco_client import LocoClient
from unitree_sdk2py.g1.audio.g1_audio_client import AudioClient
from unitree_sdk2py.comm.motion_switcher.motion_switcher_client import MotionSwitcherClient

from unitree_sdk2py.idl.default import unitree_hg_msg_dds__LowCmd_
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowCmd_, LowState_

from unitree_sdk2py.utils.crc import CRC

logger = logging.getLogger(__name__)

# ================== 官方推荐参数 ==================
Kp = [
    60, 60, 60, 100, 40, 40,
    60, 60, 60, 100, 40, 40,
    60, 40, 40,
    40, 40, 40, 40, 40, 40, 40,
    40, 40, 40, 40, 40, 40, 40
]

Kd = [
    1, 1, 1, 2, 1, 1,
    1, 1, 1, 2, 1, 1,
    1, 1, 1,
    1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1
]


class UnitreeDriver:

    def __init__(self):
        logger.info("Initializing Unitree Driver...")

        ChannelFactoryInitialize(0, "eth0")

        # ================== 抢控制权（关键） ==================
        self.msc = MotionSwitcherClient()
        self.msc.SetTimeout(5.0)
        self.msc.Init()

        status, result = self.msc.CheckMode()
        while result['name']:
            logger.warning(f"Releasing mode: {result['name']}")
            self.msc.ReleaseMode()
            status, result = self.msc.CheckMode()
            time.sleep(1)

        logger.info("Switched to LOW-LEVEL control")

        # ================== Audio ==================
        self.audio = AudioClient()
        self.audio.Init()
        self.audio.SetTimeout(10.0)
        self.audio.SetVolume(80)

        # ================== 低层控制 ==================
        self.low_cmd = unitree_hg_msg_dds__LowCmd_()
        self.low_state = None
        self.crc = CRC()

        # DDS
        self.lowcmd_pub = ChannelPublisher("rt/lowcmd", LowCmd_)
        self.lowcmd_pub.Init()

        self.lowstate_sub = ChannelSubscriber("rt/lowstate", LowState_)
        self.lowstate_sub.Init(self._lowstate_handler, 10)

        # 控制线程
        self.running = True
        self.control_dt = 0.02  # 50Hz
        self.initialized = False  # 是否完成姿态对齐

        # 初始化电机参数
        self._init_motors()

        self.control_thread = threading.Thread(target=self._control_loop)
        self.control_thread.daemon = True
        self.control_thread.start()

        logger.info("UnitreeDriver initialized successfully")

    # ==================================================
    # 初始化电机
    # ==================================================

    def _init_motors(self):
        for i in range(len(self.low_cmd.motor_cmd)):
            self.low_cmd.motor_cmd[i].mode = 1  # enable
            self.low_cmd.motor_cmd[i].kp = Kp[i]
            self.low_cmd.motor_cmd[i].kd = Kd[i]
            self.low_cmd.motor_cmd[i].tau = 0.0
            self.low_cmd.motor_cmd[i].dq = 0.0

    # ==================================================
    # 状态回调
    # ==================================================

    def _lowstate_handler(self, msg: LowState_):
        self.low_state = msg

    # ==================================================
    # 控制主循环（核心）
    # ==================================================

    def _control_loop(self):
        logger.info("Control loop started")

        while self.running:

            if self.low_state is None:
                time.sleep(self.control_dt)
                continue

            # 初始化
            if not self.initialized:
                for i in range(len(self.low_cmd.motor_cmd)):
                    self.low_cmd.motor_cmd[i].q = self.low_state.motor_state[i].q
                self.initialized = True

            # ===== 每一帧必须完整写 =====
            self.low_cmd.mode_machine = self.low_state.mode_machine
            self.low_cmd.mode_pr = 0  # Mode.PR

            for i in range(len(self.low_cmd.motor_cmd)):
                self.low_cmd.motor_cmd[i].mode = 1
                self.low_cmd.motor_cmd[i].dq = 0.0
                self.low_cmd.motor_cmd[i].kp = Kp[i]
                self.low_cmd.motor_cmd[i].kd = Kd[i]
                self.low_cmd.motor_cmd[i].tau = 0.0

            # 发送
            self.low_cmd.crc = self.crc.Crc(self.low_cmd)
            self.lowcmd_pub.Write(self.low_cmd)

            time.sleep(self.control_dt)

    # ==================================================
    # 高层接口（给 primitives 用）
    # ==================================================

    def set_joint(self, joint_id, q):
        """设置单个关节"""
        if not self.initialized:
            return
        self.low_cmd.motor_cmd[joint_id].q = q

    def set_joints(self, joints_dict):
        """设置多个关节"""
        if not self.initialized:
            return
        for jid, q in joints_dict.items():
            self.low_cmd.motor_cmd[jid].q = q

    # ==================================================
    # audio
    # ==================================================

    def speak(self, text, volume=80):
        self.audio.SetVolume(volume)
        self.audio.TtsMaker(text, 1)

    def led(self, r, g, b):
        self.audio.LedControl(r, g, b)

    # ==================================================
    # 关闭
    # ==================================================

    def close(self):
        self.running = False
        self.control_thread.join()