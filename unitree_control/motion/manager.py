"""
总入口：
接收外部指令 & 决定做什么动作
"""
from .executor import MotionExecutor
from .sequences import SpinMotion, WaveMotion, GreetMotion


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

        elif action == "spin":
            motion = SpinMotion(
                speed=cmd.get("speed", 1.0),
                duration=cmd.get("duration", 3.0)
            )
            self.executor.execute(motion)

        elif action == "wave":
            self.executor.execute(WaveMotion())

        else:
            raise ValueError(action)

    def update(self):
        self.executor.update()

    def handle_behavior(self, name, params):
        print(f"🎬 Behavior: {name}")

        try:
            if name == "wave":
                self.executor.execute(WaveMotion())

            elif name == "spin":
                self.executor.execute(SpinMotion())

            elif name == "greet":
                person_name = params.get("person_name", "my friend")
                self.executor.execute(GreetMotion(person_name))

            else:
                print(f"⚠️ Unknown behavior: {name}")
        except Exception as e:
            print(f"❌ Error executing behavior {name}: {e}")
            import traceback
            print(traceback.format_exc())

    def handle_control(self, cmd):
        vx = cmd.get("vx", 0.0)
        vy = cmd.get("vy", 0.0)
        theta = cmd.get("theta", 0.0)

        self.driver.move(vx, vy, theta)

    def greet(self, name):
        return [
            lambda: self.driver.set_led(0, 255, 0),
            lambda: self.driver.speak(f"Hello {name}"),
            WaveMotion(),
            lambda: self.driver.set_led(0, 0, 0),
        ]