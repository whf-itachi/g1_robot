# G1 Robot ROS2 Package

宇树 G1 机器人二次开发 ROS2 包，实现人脸识别、运动控制和智能交互功能。
**重构版本：采用分离架构，解决ROS2 + Unitree SDK混在单进程中导致的DDS冲突问题**

### 语音交互功能
- **音频处理**: 新增公共音频处理模块 (common.audio_handler)，提供语音输入输出功能
- **语音输出**: 通过公共音频模块提供本地语音合成功能，提升打招呼体验
- **语音输入**: 集成语音识别功能，支持语音交互（预留接口）
- **设备兼容**: 自动适配各种音频设备（麦克风、扬声器）

## 📦 包结构

```
g1_robot/
├── data/
│   └── face_database.json      # 人脸特征数据库
├── unitree_control_server.py   # Unitree SDK控制服务器（独立进程）
├── start_system.sh             # 系统启动脚本
├── src/
│   ├── common/                 # 共享组件,unitree sdk调用以及音频的输出输出模块
│   ├── g1_interfaces/          # 自定义消息接口
│   ├── g1_camera/              # 相机视频流处理
│   ├── g1_face/                # 人脸识别
│   └── g1_behavior/            # 行为响应
└── README.md
```

### 包说明

| 包名 | 功能 | 类型 | 主要节点 |
|------|------|------|----------|
| `g1_interfaces` | 自定义消息接口 | ament_cmake | - |
| `g1_camera` | 视频流解码/USB 摄像头 | ament_python | `camera_node` |
| `g1_face` | InsightFace 人脸识别 | ament_python | `face_node` |
| `g1_behavior` | 面部行为响应（支持打招呼、企业微信通知等） | ament_python | `face_behavior_node` |

## 🔧 环境要求

- **ROS2 版本**: Humble / Jazzy
- **Python**: 3.10+
- **操作系统**: Ubuntu 22.04+ (或 Windows 10/11 WSL2)

### Python 依赖

```bash
pip install insightface opencv-python numpy websocket-client pytz requests
```

### 语音功能依赖（可选）

```bash
pip install pyttsx3      # 文本转语音
pip install vosk         # 语音识别  
pip install sounddevice  # 音频输入输出
```

### 宇树 SDK

确保已安装 `unitree_sdk2py`：

```bash
# 参考官方文档安装
# https://github.com/unitreerobotics/unitree_sdk2_python
```

## 🚀 新架构说明

### 问题背景
旧架构中ROS2和Unitree SDK混合在同一个进程中，导致DDS通信冲突，使机器人无法执行动作。

### 解决方案
采用分离架构：
1. **Unitree控制服务器** (`unitree_control_server.py`): 独立进程，专门处理Unitree SDK操作
2. **ROS2节点**: 通过socket与控制服务器通信，避免DDS冲突

### 系统架构图
```
┌─────────────────────────────────────────────────────────────┐
│                      G1 机器人                               │
│  ┌─────────────┐                                         ┌─────────────┐   │
│  │ 前置摄像头   │──┐                                   │ 运动执行器   │   │
│  └─────────────┘  │    ┌─────────────┐               └──────▲──────┘   │
│                   ▼    │ video stream│                      │          │
│                  /c920/image_raw    └────────────────────────┼──────────┘
└──────────────────────────────────────────────────────────────┼──────────┘
                                                             │
         ┌────────────────────┼────────────────────┼──────────┐
         │  ROS2              │                    │          │
         │                    ▼                    │          │
         │  ┌──────────────────────────┐          │          │
         │  │   face_node              │          │          │
         │  │   (人脸识别)             │          │          │
         │  └─────────────┬────────────┘          │          │
         │                │ /face/result          │          │
         │                ▼                       │          │
         │  ┌──────────────────────────┐          │          │
         │  │   face_behavior_node     │          │          │
         │  │   (面部行为响应)         │          │          │
         │  └──────────────────────────┘          │          │
         │                                        │          │
         └────────────────────────────────────────────────────┘
                                    │
                                    ▼
                    ┌──────────────────────────┐
                    │   Unitree Control        │
                    │   Server (独立进程)      │
                    │   (SDK + 机器人通信)     │
                    │   - 动作队列: 串行执行动作│
                    │   - 语音队列: 串行执行语音│
                    │   - 支持动作语音并行    │
                    └──────────────────────────┘
```

## 🚀 快速开始

### 1. 构建项目

```bash
cd ~/g1_robot
colcon build
source install/setup.bash
```

### 2. 启动系统

**方式一：使用启动脚本（推荐）**
```bash
# Linux/Mac
chmod +x start_system.sh
./start_system.sh
```

**方式二：手动启动**

1. 启动Unitree控制服务器（独立终端）：
```bash
cd ~/g1_robot
python -m unitree_control.server
```

2. 启动ROS2系统（另一个终端）：
```bash
cd ~/g1_robot
colcon build
source install/setup.bash
ros2 launch g1_behavior g1_system.launch.py
```

## 📡 话题列表

### 发布的话题

| 话题名 | 消息类型 | 发布节点 |
|--------|----------|----------|
| `/face/result` | `g1_interfaces/msg/FaceResult` | `face_node` |

### 订阅的话题

| 话题名 | 消息类型 | 订阅节点 |
|--------|----------|----------|
| `/frontvideostream` | `unitree_go/msg/Go2FrontVideoData` | `camera_node` |
| `/c920/image_raw` | `sensor_msgs/msg/Image` | `face_node`, `face_behavior_node` |
| `/face/result` | `g1_interfaces/msg/FaceResult` | `face_behavior_node` |

## 📝 自定义消息

### FaceResult.msg

```msg
string name         # 识别出的人名
float32 similarity  # 相似度 (0.0-1.0)
string source       # 识别来源
```

## 🛠️ 调试命令

现在所有机器人控制都通过 `unitree_control_server.py` 实现，无需单独的调试节点。

## 🔍 故障排查

### 问题：无法打开摄像头

```bash
# 检查摄像头设备
ls -l /dev/video*

# 检查权限
sudo chmod 666 /dev/video0
```

### 问题：Unitree控制服务器连接失败

确保Unitree控制服务器已启动：
```bash
python -m unitree_control.server
```

### 问题：人脸识别率低

- 确保光线充足
- 调整摄像头角度
- 更新人脸数据库中的特征向量

## 📄 许可证

Apache-2.0 License

## 👤 维护者

Nathan <service02@haitch.cn>