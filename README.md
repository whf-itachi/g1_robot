# G1 Robot ROS2 Package

宇树 G1 机器人二次开发 ROS2 包，实现人脸识别、运动控制和智能交互功能。

## 📦 包结构

```
g1_robot/
├── data/
│   └── face_database.json      # 人脸特征数据库
├── src/
│   ├── g1_interfaces/          # 自定义消息接口
│   ├── g1_camera/              # 相机视频流处理
│   ├── g1_face/                # 人脸识别
│   ├── g1_motion/              # 运动控制
│   └── g1_behavior/            # 行为响应
└── README.md
```

### 包说明

| 包名 | 功能 | 类型 | 主要节点 |
|------|------|------|----------|
| `g1_interfaces` | 自定义消息接口 | ament_cmake | - |
| `g1_camera` | 视频流解码/USB 摄像头 | ament_python | `camera_node`, `face_node_direct` |
| `g1_face` | InsightFace 人脸识别 | ament_python | `face_node` |
| `g1_motion` | unitree_sdk2py 运动控制 | ament_python | `motion_node`, `g1_debug` |
| `g1_behavior` | 问候和交互行为 | ament_python | `greeting_node` |

## 🔧 环境要求

- **ROS2 版本**: Humble / Jazzy
- **Python**: 3.10+
- **操作系统**: Ubuntu 22.04+

### Python 依赖

```bash
pip install insightface opencv-python numpy
```

### 宇树 SDK

确保已安装 `unitree_sdk2py`：

```bash
# 参考官方文档安装
# https://github.com/unitreerobotics/unitree_sdk2_python
```

## 🚀 快速开始

### 1. 构建项目

```bash
cd ~/g1_robot
colcon build
source install/setup.bash
```

### 2. 启动完整系统

```bash
ros2 launch g1_behavior g1_system.launch.py
```

系统会自动启动以下节点：
1. `motion_node` - 运动控制
2. `face_node_direct` - USB 摄像头图像发布
3. `face_node` - 人脸识别
4. `greeting_node` - 问候行为响应

### 3. 单独启动节点

```bash
# 运动控制节点
ros2 run g1_motion motion_node

# 人脸识别节点
ros2 run g1_face face_node

# 行为响应节点
ros2 run g1_behavior greeting_node

# G1 调试控制台（手动控制机器人动作）
ros2 run g1_motion g1_debug
```

## 📡 话题列表

### 发布的话题

| 话题名 | 消息类型 | 发布节点 |
|--------|----------|----------|
| `/face/result` | `g1_interfaces/msg/FaceResult` | `face_node` |
| `/motion/cmd` | `g1_interfaces/msg/MotionCmd` | `greeting_node` |
| `/camera/standard_image` | `sensor_msgs/msg/Image` | `face_node_direct` |

### 订阅的话题

| 话题名 | 消息类型 | 订阅节点 |
|--------|----------|----------|
| `/frontvideostream` | `unitree_go/msg/Go2FrontVideoData` | `camera_node` |
| `/camera/standard_image` | `sensor_msgs/msg/Image` | `face_node` |
| `/face/result` | `g1_interfaces/msg/FaceResult` | `greeting_node` |
| `/motion/cmd` | `g1_interfaces/msg/MotionCmd` | `motion_node` |

## 📝 自定义消息

### FaceResult.msg

```msg
string name         # 识别出的人名
float32 similarity  # 相似度 (0.0-1.0)
string source       # 识别来源
```

### MotionCmd.msg

```msg
string cmd          # 动作命令 (如 "wave_hand", "stop")
string param        # 动作参数
```

## 🛠️ 调试命令

使用 `g1_debug` 节点手动控制机器人：

```bash
ros2 run g1_motion g1_debug
```

可用命令：
- `wave` - 挥手
- `shake` - 握手
- `sit` - 坐下
- `stand` - 站立
- `move` - 移动
- `stop` - 停止
- `quit` - 退出

## 📊 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      G1 机器人                               │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐   │
│  │ 前置摄像头   │────▶│ video stream│     │ 运动执行器   │   │
│  └─────────────┘     └──────┬──────┘     └──────▲──────┘   │
└─────────────────────────────┼────────────────────┼──────────┘
                              │                    │
         ┌────────────────────┼────────────────────┼──────────┐
         │  ROS2              │                    │          │
         │                    ▼                    │          │
         │  ┌──────────────────────────┐          │          │
         │  │   face_node_direct       │          │          │
         │  │   (USB 摄像头图像发布)     │          │          │
         │  └──────────────────────────┘          │          │
         │                    │                    │          │
         │                    ▼                    │          │
         │  ┌──────────────────────────┐          │          │
         │  │   face_node              │          │          │
         │  │   (人脸识别)             │          │          │
         │  └─────────────┬────────────┘          │          │
         │                │ /face/result          │          │
         │                ▼                       │          │
         │  ┌──────────────────────────┐          │          │
         │  │   greeting_node          │          │          │
         │  │   (行为决策)             │          │          │
         │  └─────────────┬────────────┘          │          │
         │                │ /motion/cmd           │          │
         │                ▼                       │          │
         │  ┌──────────────────────────┐          │          │
         │  │   motion_node            │──────────┘          │
         │  │   (运动控制)             │                     │
         │  └──────────────────────────┘                     │
         └───────────────────────────────────────────────────┘
```

## 🔍 故障排查

### 问题：无法打开摄像头

```bash
# 检查摄像头设备
ls -l /dev/video*

# 检查权限
sudo chmod 666 /dev/video0
```

### 问题：SDK 初始化失败

确保机器人已连接且网络配置正确：

```bash
# 检查网络连接
ping 192.168.3.1
```

### 问题：人脸识别率低

- 确保光线充足
- 调整摄像头角度
- 更新人脸数据库中的特征向量

## 📄 许可证

Apache-2.0 License

## 👤 维护者

Nathan <service02@haitch.cn>
