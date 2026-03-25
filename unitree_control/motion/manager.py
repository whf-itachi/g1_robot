"""
manager.py
总入口：接收外部指令 & 决定做什么动作
"""
import logging
from .executor import MotionExecutor
from .sequences import GreetMotion, TestMotion

# 获取logger实例
logger = logging.getLogger(__name__)


class MotionManager:

    def __init__(self, driver):
        self.driver = driver
        from .primitives import MotionPrimitives
        self.primitives = MotionPrimitives(driver)
        self.executor = MotionExecutor(self.primitives)

    def handle(self, cmd):
        action = cmd.get("action")

        if action == "move":
            self.executor.stop()
            self.primitives.move(
                cmd.get("vx", 0),
                cmd.get("vy", 0),
                cmd.get("theta", 0)
            )

        elif action == "stop_move":
            self.executor.stop()
        else:
            raise ValueError(action)

    def update(self):
        self.executor.update()

    def handle_behavior(self, name, params):
        logger.info(f"Behavior: {name}")

        if name == "greet":
            person_name = params.get("person_name", "my friend")
            logger.info(f"Greeting {person_name}")
            self.executor.execute(TestMotion())  # 测试用，看看是否能够执行
            # self.executor.execute(GreetMotion(person_name))

        else:
            logger.warning(f"Unknown behavior: {name}")

    def handle_control(self, cmd):
        vx = cmd.get("vx", 0.0)
        vy = cmd.get("vy", 0.0)
        theta = cmd.get("theta", 0.0)

        self.driver.move(vx, vy, theta)