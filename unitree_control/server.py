#!/usr/bin/env python3

import socket
import json
import struct
import threading
import queue
import time

from unitree_control.driver.unitree_driver import UnitreeDriver
from unitree_control.motion.manager import MotionManager
from unitree_control.logger_config import logger as main_logger


class UnitreeControlServer:

    def __init__(self, host="127.0.0.1", port=9090):
        self.host = host
        self.port = port

        main_logger.info("Initializing Unitree Control Server...")

        # ==========================
        # Driver + Motion System
        # ==========================
        self.driver = UnitreeDriver()  # 通过它控制机器人
        self.motion_manager = MotionManager(self.driver)

        # ==========================
        # Queues
        # ==========================
        self.action_queue = queue.Queue()
        self.speech_queue = queue.Queue()

        self.running = True

        # ==========================
        # Threads
        # ==========================
        self.action_thread = threading.Thread(
            target=self.action_worker,
            daemon=True
        )

        self.speech_thread = threading.Thread(
            target=self.speech_worker,
            daemon=True
        )

        self.motion_thread = threading.Thread(
            target=self.motion_loop,
            daemon=True
        )

        self.action_thread.start()
        self.speech_thread.start()
        self.motion_thread.start()

        # ==========================
        # Socket Server
        # ==========================
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)

        main_logger.info(f"Server listening on {self.host}:{self.port}")

    # =========================================================
    # Command Handling
    # =========================================================
    def handle_command(self, cmd_data):
        try:
            cmd = json.loads(cmd_data)
            cmd_type = cmd.get("type")

            # ==========================
            # 行为 → 走 action_queue
            # ==========================
            if cmd_type == "behavior":
                self.action_queue.put(cmd)

            # ==========================
            # 控制（连续）→ 直接交给 motion_manager
            # ==========================
            elif cmd_type == "control":
                self.motion_manager.handle_control(cmd)

            # ==========================
            # 语音 → speech_queue
            # ==========================
            elif cmd_type == "speech":
                self.speech_queue.put(cmd)

            # ==========================
            # LED → 直接 driver
            # ==========================
            elif cmd_type == "led":
                self.driver.set_led(
                    cmd.get("r", 0),
                    cmd.get("g", 0),
                    cmd.get("b", 0)
                )

            else:
                return {"status": "error", "message": "unknown type"}

            return {"status": "success"}

        except Exception as e:
            main_logger.error(f"Command error: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    # =========================================================
    # Workers
    # =========================================================
    def action_worker(self):
        main_logger.info("Action worker started")

        while self.running:
            try:
                cmd = self.action_queue.get(timeout=1)
                if cmd is None:
                    continue

                try:
                    # 统一入口
                    main_logger.debug(f"Handling behavior: {cmd.get('name')} with params: {cmd.get('params', {})}")
                    self.motion_manager.handle_behavior(
                        cmd.get("name"),
                        cmd.get("params", {})
                    )
                    main_logger.info(f"Behavior '{cmd.get('name')}' completed successfully")
                except Exception as e:
                    main_logger.error(f"Motion error: {e}", exc_info=True)

                self.action_queue.task_done()

            except queue.Empty:
                continue

    def speech_worker(self):
        main_logger.info("Speech worker started")

        while self.running:
            try:
                cmd = self.speech_queue.get(timeout=1)
                if cmd is None:
                    continue

                text = cmd.get("text", "")
                volume = cmd.get("volume", 80)

                main_logger.info(f"Speaking: '{text[:50]}{'...' if len(text) > 50 else ''}' at volume {volume}")
                self.driver.speak(text, volume)

                self.speech_queue.task_done()

            except queue.Empty:
                continue

    def motion_loop(self):
        """
        核心循环（非阻塞）
        负责推进 MotionExecutor
        """
        main_logger.info("Motion loop started (50Hz)")

        while self.running:
            try:
                self.motion_manager.update()
                time.sleep(0.02)  # 50Hz

            except Exception as e:
                main_logger.error(f"Motion loop error: {e}", exc_info=True)

    # =========================================================
    # Socket Handling
    # =========================================================
    def handle_client(self, conn, addr):
        main_logger.info(f"Connected: {addr}")

        try:
            while True:
                # ===== 读取长度 =====
                length_data = conn.recv(4)
                if not length_data:
                    break

                cmd_length = struct.unpack('!I', length_data)[0]

                # ===== 读取数据 =====
                cmd_data = b''
                while len(cmd_data) < cmd_length:
                    chunk = conn.recv(cmd_length - len(cmd_data))
                    if not chunk:
                        break
                    cmd_data += chunk

                if not cmd_data:
                    break

                # ===== 处理命令 =====
                main_logger.debug(f"Received command from {addr}: {cmd_data.decode('utf-8')[:100]}...")
                response = self.handle_command(cmd_data.decode('utf-8'))
                main_logger.debug(f"Sending response to {addr}: {response}")

                # ===== 返回响应 =====
                response_bytes = json.dumps(response).encode('utf-8')

                conn.sendall(struct.pack('!I', len(response_bytes)))
                conn.sendall(response_bytes)

        except ConnectionResetError:
            main_logger.warning(f"Client disconnected unexpectedly: {addr}")

        except Exception as e:
            main_logger.error(f"Client error: {e}", exc_info=True)

        finally:
            try:
                conn.close()
            except:
                pass

            main_logger.info(f"Connection closed: {addr}")

    # =========================================================
    # Main Loop
    # =========================================================
    def start(self):
        main_logger.info("Unitree Control Server started")

        try:
            while True:
                conn, addr = self.server_socket.accept()

                main_logger.debug(f"Accepting connection from {addr}")
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(conn, addr),
                    daemon=True
                )
                client_thread.start()

        except KeyboardInterrupt:
            main_logger.info("\n KeyboardInterrupt received")
            self.shutdown()

        except Exception as e:
            main_logger.error(f"Server fatal error: {e}", exc_info=True)
            self.shutdown()

    # =========================================================
    # Shutdown
    # =========================================================
    def shutdown(self):
        main_logger.info("Shutting down server...")
        self.running = False

        try:
            self.action_queue.put(None)
            self.speech_queue.put(None)
        except Exception as e:
            main_logger.error(f"Error putting None to queues: {e}")

        try:
            self.server_socket.close()
        except Exception as e:
            main_logger.error(f"Error closing server socket: {e}")

        main_logger.info("Server stopped")


# =========================================================
# Entry
# =========================================================
def main():
    server = UnitreeControlServer()
    server.start()


if __name__ == "__main__":
    main()