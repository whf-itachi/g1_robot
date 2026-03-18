import time
import threading
import traceback
import numpy as np
from unitree_sdk2py.g1.loco.g1_loco_client import LocoClient
from unitree_sdk2py.core.channel import ChannelPublisher, ChannelSubscriber
from unitree_sdk2py.idl.default import unitree_hg_msg_dds__LowCmd_
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowCmd_, LowState_
from unitree_sdk2py.utils.crc import CRC


class G1JointIndex:
    """G1机器人关节索引定义"""
    R_SHOULDER_PITCH = 22
    R_SHOULDER_ROLL = 23
    R_SHOULDER_YAW = 24
    R_ELBOW = 25
    R_WRIST_ROLL = 26
    R_WRIST_PITCH = 27
    R_WRIST_YAW = 28


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
        try:
            self.motion = LocoClient()
            self.motion.SetTimeout(10.0)
            self.motion.Init()
            self.motion.WaitLeaseApplied()
            self.motion.Start()
            self.motion.HighStand()
            
            # 低层控制相关
            self.control_dt_ = 0.02
            self.low_cmd = unitree_hg_msg_dds__LowCmd_()
            self.low_state = None
            self.crc = CRC()
            
            # 低层控制发布者和订阅者
            self.lowcmd_publisher = ChannelPublisher("rt/lowcmd", LowCmd_)
            self.lowcmd_publisher.Init()
            self.lowstate_subscriber = ChannelSubscriber("rt/lowstate", LowState_)
            self.lowstate_subscriber.Init(self._low_state_handler, 10)
            
            # 右臂关节配置
            self.arm_joints = [
                G1JointIndex.R_SHOULDER_PITCH,
                G1JointIndex.R_SHOULDER_ROLL,
                G1JointIndex.R_SHOULDER_YAW,
                G1JointIndex.R_ELBOW,
                G1JointIndex.R_WRIST_ROLL,
                G1JointIndex.R_WRIST_PITCH,
                G1JointIndex.R_WRIST_YAW,
            ]
            
            # 配置电机参数
            for joint in self.arm_joints:
                self.low_cmd.motor_cmd[joint].mode = 1
                self.low_cmd.motor_cmd[joint].kp = 100.0
                self.low_cmd.motor_cmd[joint].kd = 3.0
                self.low_cmd.motor_cmd[joint].tau = 0.0

        except Exception as e:
            print(f"Error initializing LocoClient: {e}")
            print(traceback.format_exc())
            raise

        self._state = "IDLE"
        self._lock = threading.Lock()
        
        # 自然问候动作参数
        self.duration_ = 4.0  # 动作持续时间
        self.time_ = 0.0
        self.target_pos = [-0.5, -0.5, -0.5, -0.5, -1, 0, 0]  # 目标位置
        self.wrist_pitch_target_delta = 0.8  # 手腕摆动幅度
        self.swing_frequency = 1.0  # 摆动频率

    def _low_state_handler(self, msg):
        """低层状态处理函数"""
        self.low_state = msg

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
        try:
            if self._get_state() == "STOPPING":
                return

            self._set_state("STOPPING")
            self.motion.StopMove()
            self._set_state("IDLE")
        except Exception as e:
            print(f"Error stopping robot: {e}")
            print(traceback.format_exc())

    def wave_hand(self):
        """执行挥手/握手动作"""
        try:
            print(f"[DEBUG] Starting wave_hand method")
            current_state = self._get_state()
            print(f"[DEBUG] Current state in wave_hand: {current_state}")

            if current_state == "GREETING":
                print(f"[DEBUG] Already in GREETING state, returning early")
                return
            if current_state in ["STOPPING", "MOVING"]:
                print(f"[DEBUG] Current state is {current_state}, calling stop()")
                self.stop()

            print(f"[DEBUG] Setting state to GREETING")
            self._set_state("GREETING")
            print(f"[DEBUG] Calling motion.ShakeHand()")
            self.motion.ShakeHand()
            print(f"[DEBUG] ShakeHand called, sleeping for 10.0 seconds")
            time.sleep(10.0)  # 修改为等待10秒
            print(f"[DEBUG] Calling HighStand to return to standing position")
            self.motion.HighStand()
            print(f"[DEBUG] Setting state back to IDLE")
            self._set_state("IDLE")
            print(f"[DEBUG] wave_hand method completed successfully")
        except Exception as e:
            print(f"Error executing wave hand: {e}")
            print(traceback.format_exc())
            # 确保状态被重置
            print(f"[DEBUG] Error occurred, resetting state to IDLE")
            self._set_state("IDLE")

    def natural_greeting(self):
        """执行更自然的问候动作，包含手臂移动和手腕摆动"""
        try:
            current_state = self._get_state()
            if current_state == "GREETING":
                return
            if current_state in ["STOPPING", "MOVING"]:
                self.stop()

            self._set_state("GREETING")
            
            # 启动自然问候动作控制循环
            self.time_ = 0.0
            start_time = time.time()
            
            while self.time_ < 3 * self.duration_ and self._get_state() == "GREETING":
                current_time = time.time()
                self.time_ = current_time - start_time
                
                if self.low_state is not None:
                    self._execute_natural_greeting_step()
                
                time.sleep(self.control_dt_)
            
            # 完成动作后回到站立状态
            self.motion.HighStand()
            self._set_state("IDLE")
            
        except Exception as e:
            print(f"Error executing natural greeting: {e}")
            print(traceback.format_exc())
            # 确保状态被重置
            self._set_state("IDLE")

    def _execute_natural_greeting_step(self):
        """执行自然问候动作的一个步骤"""
        try:
            self.low_cmd.mode_machine = self.low_state.mode_machine
            self.low_cmd.mode_pr = 0

            if self.time_ < self.duration_:
                # 第一阶段：手臂抬起
                ratio = np.clip(self.time_ / self.duration_, 0, 1)
                for i, joint in enumerate(self.arm_joints):
                    current_pos = self.low_state.motor_state[joint].q
                    target_q = current_pos + ratio * (self.target_pos[i] - current_pos)
                    self.low_cmd.motor_cmd[joint].q = target_q

            elif self.time_ < 2 * self.duration_:
                # 第二阶段：手腕摆动
                stage_time = self.time_ - self.duration_
                for i, joint in enumerate(self.arm_joints):
                    if joint != G1JointIndex.R_WRIST_PITCH:
                        self.low_cmd.motor_cmd[joint].q = self.target_pos[i]
                # 手腕摆动
                pitch_angle = self.wrist_pitch_target_delta * np.sin(
                    2 * np.pi * self.swing_frequency * stage_time
                )
                self.low_cmd.motor_cmd[G1JointIndex.R_WRIST_PITCH].q = pitch_angle

            else:
                # 第三阶段：回到初始位置
                for joint in self.arm_joints:
                    self.low_cmd.motor_cmd[joint].q = self.low_state.motor_state[joint].q
                    self.low_cmd.motor_cmd[joint].kp = 100.0
                    self.low_cmd.motor_cmd[joint].kd = 3.0

            self.low_cmd.crc = self.crc.Crc(self.low_cmd)
            self.lowcmd_publisher.Write(self.low_cmd)

        except Exception as e:
            print(f"Error in natural greeting step: {e}")
            print(traceback.format_exc())

    def is_moving(self):
        """判断机器人是否正在移动"""
        return self._get_state() == "MOVING"

    def is_busy(self):
        """判断机器人是否忙碌（不可接受新指令）"""
        return self._get_state() in ["STOPPING", "GREETING", "MOVING"]
