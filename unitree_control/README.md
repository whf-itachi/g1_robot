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

# 日志系统
本服务包含完整的日志记录功能：
- 日志文件保存在 `unitree_control/logs/` 目录下
- 主日志文件名为 `unitree_control.log`
- 支持日志轮转：单个文件最大5MB，最多保留5个历史文件
- 日志级别包括 DEBUG, INFO, WARNING, ERROR, CRITICAL
- 同时输出到控制台和文件，便于实时监控和长期分析