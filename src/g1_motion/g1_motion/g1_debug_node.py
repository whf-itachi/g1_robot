import rclpy
from rclpy.node import Node
import threading
import time

from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from .motion_controller import MotionController


class G1DebugNode(Node):

    def __init__(self):
        super().__init__("g1_debug_node")

        self.get_logger().info("Initializing SDK...")

        ChannelFactoryInitialize(0)

        self.controller = MotionController()

        self.get_logger().info("G1 Debug Console Ready")

        thread = threading.Thread(target=self.console_loop)
        thread.daemon = True
        thread.start()

    def console_loop(self):

        while True:

            cmd = input(
                "\nCommands: wave | shake | sit | stand | move | stop | quit\n> "
            )

            if cmd == "wave":
                self.controller.wave_hand()

            elif cmd == "shake":
                self.controller.motion.ShakeHand()
                time.sleep(1.0)
                self.controller.motion.HighStand()

            elif cmd == "sit":
                self.controller.motion.Sit()

            elif cmd == "stand":
                self.controller.motion.HighStand()

            elif cmd == "move":
                self.controller.motion.Move(0.2, 0.0, 0.0)

            elif cmd == "stop":
                self.controller.stop()

            elif cmd == "quit":
                break

            else:
                print("Unknown command")


def main(args=None):

    rclpy.init(args=args)

    node = G1DebugNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    node.destroy_node()
    rclpy.shutdown()