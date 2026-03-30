from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.g1.loco.g1_loco_client import LocoClient
from unitree_sdk2py.g1.arm.g1_arm_action_client import G1ArmActionClient
from unitree_sdk2py.g1.arm.g1_arm_action_client import action_map

from unitree_sdk2py.g1.audio.g1_audio_client import AudioClient


class UnitreeDriver:

    def __init__(self):
        print("Initializing Unitree SDK...")
        ChannelFactoryInitialize(0, "eth0")

        self.loco = LocoClient()
        self.loco.SetTimeout(10.0)
        self.loco.Init()

        self.armAction_client = G1ArmActionClient()
        self.armAction_client.SetTimeout(10.0)
        self.armAction_client.Init()

        self.audio = AudioClient()
        self.audio.Init()
        self.audio.SetTimeout(10.0)
        self.audio.SetVolume(80)

        print("✅ UnitreeDriver initialized")

    # ===== locomotion =====
    def move(self, vx, vy, yaw):
        self.loco.Move(vx, vy, yaw)

    def stop(self):
        self.loco.StopMove()

    def stand(self):
        self.loco.HighStand()

    def sit(self):
        self.loco.Sit()

    def shake_hand(self):
        self.loco.ShakeHand()

    def face_wave(self):
        self.armAction_client.ExecuteAction(action_map.get("face wave"))

    # ===== audio =====
    def speak(self, text, volume=80):
        self.audio.SetVolume(volume)
        self.audio.TtsMaker(text, 1)

    def led(self, r, g, b):
        self.audio.LedControl(r, g, b)