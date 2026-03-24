"""
总入口：
接收外部指令 & 决定做什么动作
"""
from .executor import MotionExecutor
from .sequences import GreetMotion


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
        print(f"🎬 Behavior: {name}")

        if name == "greet":
            person_name = params.get("person_name", "my friend")
            self.executor.execute(GreetMotion(person_name))

        else:
            print(f"⚠️ Unknown behavior: {name}")

    def handle_control(self, cmd):
        vx = cmd.get("vx", 0.0)
        vy = cmd.get("vy", 0.0)
        theta = cmd.get("theta", 0.0)

        self.driver.move(vx, vy, theta)