# 机器人驱动服务 Driver Service
unitree_control 本质是一个：指令 → 解析 → 调度 → 动作执行器 → 底层驱动 的流水线
一个独立进程运行的：
- 机器人控制中间件（非ROS）
- 通过 socket 提供控制能力
- 内部包含 motion system（运动系统）

# 项目启动
python3 -m unitree_control.server


# 执行流程
manager.py 大脑决定：挥手
   ↓
executor.py  控制节奏：开始 / 继续 / 停止
   ↓
sequences.py 挥手分3步
   ↓
primitives.py 控制手臂怎么动
   ↓
(driver) 机器人SDK控制怎么动


# 项目架构
ROS2
 ↓
UnitreeClient
 ↓
Socket
 ↓
handle_command
 ↓
┌───────────────┬───────────────┐
│ action_queue  │ speech_queue  │
└───────┬───────┴───────┬───────┘
        ↓               ↓
   MotionManager     driver.speak
        ↓
   MotionExecutor
        ↓
      SDK