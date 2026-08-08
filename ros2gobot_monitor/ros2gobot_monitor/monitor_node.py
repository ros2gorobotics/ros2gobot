#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rcl_interfaces.msg import Log
from ros2gobot_msgs.msg import RobotLog, RobotStatus

import psutil
import os

class MonitorNode(Node):
    def __init__(self):
        super().__init__("ros2gobot_monitor")

        # ---------------------------------------------------------
        # 1. Subscribers (เหลือแค่ Log เพราะเราต้องเอาไปโชว์หน้าเว็บ)
        # ---------------------------------------------------------
        self.sub_rosout = self.create_subscription(
            Log, "/rosout", self.log_callback, 10
        )
        
        # ❌ ลบ Subscribe ของ Lidar, IMU, ODOM, TF ทิ้งทั้งหมด!
        # เราจะไม่ให้ Python ต้องมาประมวลผลข้อความความถี่สูงอีกต่อไป

        # ---------------------------------------------------------
        # 2. Publishers
        # ---------------------------------------------------------
        self.pub_log = self.create_publisher(RobotLog, "/robot/log", 10)
        self.pub_status = self.create_publisher(RobotStatus, "/robot/status", 5)

        # ---------------------------------------------------------
        # 3. Timers & State Variables
        # ---------------------------------------------------------
        self.timer_status = self.create_timer(1.0, self.status_timer_callback)

        self.battery_level = 100.0
        self.navigation_active = False
        self.mapping_active = False
        self.node_check_counter = 0

        self.get_logger().info("ROS2GO Monitor Node started (Ultra-Low CPU Version).")

    def log_callback(self, msg):
        """จัดการ Log จาก /rosout"""
        if msg.level < 20: return
        
        out_msg = RobotLog()
        out_msg.level = msg.level
        out_msg.node = msg.name
        out_msg.message = msg.msg
        out_msg.stamp = msg.stamp
        
        self.pub_log.publish(out_msg)

    # --- ฟังก์ชันอ่านอุณหภูมิ CPU สำหรับ RPi ---
    def get_cpu_temp(self):
        try:
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                return float(f.read()) / 1000.0
        except Exception:
            return 0.0

    def status_timer_callback(self):
        """ตรวจสอบสถานะระบบทุก 1 วินาที"""
        # 1. เช็ค Mapping/Navigation mode จาก Node List (ทุกๆ 10 วินาที)
        self.node_check_counter += 1
        if self.node_check_counter >= 10:
            node_names = self.get_node_names()
            self.mapping_active = any('slam_toolbox' in str(name).lower() for name in node_names)
            self.navigation_active = any('bt_navigator' in str(name).lower() for name in node_names)
            self.node_check_counter = 0
            
        # 2. เช็ค Sensor Status ด้วย count_publishers 
        # 👉 กิน CPU แทบจะเป็น 0% เพราะไม่ต้องถอดรหัสข้อความ แค่เช็คว่ามี Node ไหนปล่อย Topic นี้อยู่ไหม
        lidar_ok = self.count_publishers('/scan') > 0
        imu_ok = self.count_publishers('/imu/data') > 0
        odom_ok = self.count_publishers('/odom') > 0
        tf_ok = self.count_publishers('/tf') > 0

        # สร้างข้อความสถานะ
        status_msg = RobotStatus()
        
        # System Resources
        status_msg.cpu = float(psutil.cpu_percent(interval=None))
        status_msg.cpu_temp = float(self.get_cpu_temp())
        status_msg.ram = float(psutil.virtual_memory().percent)
        status_msg.disk = float(psutil.disk_usage('/').percent)
        status_msg.battery = self.battery_level
        
        # Process Status
        status_msg.navigation_active = self.navigation_active
        status_msg.mapping_active = self.mapping_active
        
        # Sensor Status
        status_msg.lidar_status = lidar_ok        
        status_msg.imu_status = imu_ok
        status_msg.odom_status = odom_ok
        status_msg.tf_status = tf_ok
        
        # การประเมินสถานะระบบหลัก
        status_msg.hardware_status = imu_ok and odom_ok
        status_msg.localization_status = tf_ok

        # Publish
        self.pub_status.publish(status_msg)

def main(args=None):
    rclpy.init(args=args)
    node = MonitorNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Shutting down ROS2GO Monitor Node...")
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == '__main__':
    main()
