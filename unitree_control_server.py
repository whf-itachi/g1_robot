#!/usr/bin/env python3
"""
Unitree G1 机器人控制服务器
此服务器独立运行，专门处理Unitree SDK相关的操作
通过socket与ROS2节点通信，避免DDS冲突
"""

import socket
import json
import struct
import threading
import queue
import traceback
from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.g1.loco.g1_loco_client import LocoClient
from unitree_sdk2py.g1.audio.g1_audio_client import AudioClient


class UnitreeControlServer:
    def __init__(self, host="127.0.0.1", port=9090):
        self.host = host
        self.port = port
        
        # 初始化SDK（仅在此进程中初始化）
        print("Initializing Unitree SDK...")
        ChannelFactoryInitialize(0, "eth0")
        
        # 初始化客户端
        self.loco_client = LocoClient()
        self.loco_client.SetTimeout(10.0)
        self.loco_client.Init()
        
        self.audio_client = AudioClient()
        self.audio_client.Init()
        self.audio_client.SetTimeout(10.0)
        self.audio_client.SetVolume(80)
        
        # 创建动作和语音队列
        self.action_queue = queue.Queue()
        self.speech_queue = queue.Queue()
        
        # 启动动作和语音处理线程
        self.action_thread = threading.Thread(target=self.action_worker, daemon=True)
        self.speech_thread = threading.Thread(target=self.speech_worker, daemon=True)
        self.running = True
        
        self.action_thread.start()
        self.speech_thread.start()
        
        print("✅ Unitree Control Server Initialized")
        
        # 创建socket服务器
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        print(f"🚀 Unitree Control Server listening on {self.host}:{self.port}")

    def handle_command(self, cmd_data):
        """处理来自ROS2节点的命令"""
        try:
            cmd = json.loads(cmd_data)
            action = cmd.get("action")
            
            print(f"Received command: {action}")
            
            # 根据命令类型放入相应队列
            if action in ["shake_hand", "high_stand", "sit", "stop_move", "move", "led_control"]:
                # 动作命令放入动作队列
                self.action_queue.put(cmd)
                return {"status": "success", "message": f"Action '{action}' queued for execution"}
                
            elif action in ["speak"]:
                # 语音命令放入语音队列
                self.speech_queue.put(cmd)
                return {"status": "success", "message": f"Speech '{action}' queued for execution"}
                
            else:
                error_msg = f"Unknown action: {action}"
                print(error_msg)
                return {"status": "error", "message": error_msg}
                
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON: {str(e)}"
            print(error_msg)
            return {"status": "error", "message": error_msg}
            
        except Exception as e:
            error_msg = f"Command queuing error: {str(e)}"
            print(error_msg)
            print(traceback.format_exc())
            return {"status": "error", "message": error_msg}
    
    def action_worker(self):
        """动作处理工作线程 - 串行执行动作命令"""
        print("Action worker started")
        while self.running:
            try:
                cmd = self.action_queue.get(timeout=1)
                if cmd is None:
                    continue
                    
                action = cmd.get("action")
                
                if action == "shake_hand":
                    self.loco_client.ShakeHand()
                    print("🤝 Shake hand executed")
                    
                elif action == "high_stand":
                    self.loco_client.HighStand()
                    print("-standing- High stand executed")
                    
                elif action == "sit":
                    self.loco_client.Sit()
                    print("🪑 Sit executed")
                    
                elif action == "stop_move":
                    self.loco_client.StopMove()
                    print("🛑 Stop move executed")
                    
                elif action == "move":
                    vx = cmd.get("vx", 0.0)
                    vy = cmd.get("vy", 0.0)
                    theta = cmd.get("theta", 0.0)
                    self.loco_client.Move(vx, vy, theta)
                    print(f"🚶 Move executed: vx={vx}, vy={vy}, theta={theta}")
                    
                elif action == "led_control":
                    r = cmd.get("r", 0)
                    g = cmd.get("g", 0)
                    b = cmd.get("b", 0)
                    self.audio_client.LedControl(r, g, b)
                    print(f"💡 LED control executed: RGB({r}, {g}, {b})")
                
                self.action_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Action worker error: {e}")
                print(traceback.format_exc())
    
    def speech_worker(self):
        """语音处理工作线程 - 串行执行语音命令"""
        print("Speech worker started")
        while self.running:
            try:
                cmd = self.speech_queue.get(timeout=1)
                if cmd is None:
                    continue
                    
                action = cmd.get("action")
                
                if action == "speak":
                    text = cmd.get("text", "")
                    volume = cmd.get("volume", 80)
                    self.audio_client.SetVolume(volume)
                    result = self.audio_client.TtsMaker(text, 1)
                    print(f"🔊 Speak executed: {text}")
                
                self.speech_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Speech worker error: {e}")
                print(traceback.format_exc())

    def start(self):
        """启动服务器主循环"""
        print("✅ Unitree Control Server Started")
        
        try:
            while True:
                try:
                    conn, addr = self.server_socket.accept()
                    print(f"🔗 Connected: {addr}")
                    
                    # 为每个连接创建新线程处理
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(conn, addr),
                        daemon=True  # 设置为守护线程
                    )
                    client_thread.start()
                    
                except Exception as e:
                    print(f"❌ Server error accepting connection: {e}")
                    print(traceback.format_exc())
        finally:
            # 优雅关闭
            self.shutdown()
    
    def handle_client(self, conn, addr):
        """处理单个客户端连接"""
        try:
            print(f"[thread-{threading.current_thread().ident}] Handling client {addr}")
            
            while True:
                # 接收命令长度（4字节）
                length_data = conn.recv(4)
                if not length_data:
                    break
                
                cmd_length = struct.unpack('!I', length_data)[0]
                
                # 接收命令数据
                cmd_data = conn.recv(cmd_length)
                if not cmd_data:
                    break
                
                # 处理命令
                response = self.handle_command(cmd_data.decode('utf-8'))
                
                # 发送响应
                response_json = json.dumps(response)
                response_bytes = response_json.encode('utf-8')
                response_length = len(response_bytes)
                
                # 先发送响应长度
                conn.sendall(struct.pack('!I', response_length))
                # 再发送响应数据
                conn.sendall(response_bytes)
            
        except ConnectionResetError:
            print(f"[thread-{threading.current_thread().ident}] Client {addr} disconnected unexpectedly")
        except Exception as e:
            print(f"[thread-{threading.current_thread().ident}] Error handling client {addr}: {e}")
            print(traceback.format_exc())
        finally:
            try:
                conn.close()
            except:
                pass
            print(f"[thread-{threading.current_thread().ident}] Closed connection: {addr}")
    
    def shutdown(self):
        """关闭服务器并清理资源"""
        print("Shutting down Unitree Control Server...")
        self.running = False
        
        # 等待队列中的任务完成
        try:
            self.action_queue.join()  # 等待所有动作任务完成
            self.speech_queue.join()  # 等待所有语音任务完成
        except:
            pass
        
        # 添加停止信号到队列以确保工作线程退出
        try:
            self.action_queue.put(None)
            self.speech_queue.put(None)
        except:
            pass
        
        print("Unitree Control Server shut down completed")


def main():
    server = UnitreeControlServer()
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down Unitree Control Server...")
        server.shutdown()
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        print(traceback.format_exc())
        server.shutdown()


if __name__ == "__main__":
    main()