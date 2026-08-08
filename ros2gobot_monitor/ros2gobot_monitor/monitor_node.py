#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rcl_interfaces.msg import Log
from ros2gobot_msgs.msg import RobotLog, RobotStatus

from sensor_msgs.msg import LaserScan, Imu
from nav_msgs.msg import Odometry
from tf2_msgs.msg import TFMessage

import psutil
import os
import time  # 👉 ใช้ standard time ของ Python เร็วกว่าของ ROS 2 มากๆ

class MonitorNode(Node):
    def __init__(self):
        super().__init__("ros2gobot_monitor")

        # ---------------------------------------------------------
        # 1. Subscribers
        # ---------------------------------------------------------
        self.sub_rosout = self.create_subscription(
            Log, "/rosout", self.log_callback, 10
        )
        
        # 👉 ปรับ Queue size เหลือ 1 เพื่อไม่ให้เก็บข้อความค้างไว้ใน RAM และลดภาระ CPU
        self.sub_scan = self.create_subscription(LaserScan, "/scan", self.scan_callback, 1)
        self.sub_imu = self.create_subscription(Imu, "/imu/data", self.imu_callback, 1)
        self.sub_odom = self.create_subscription(Odometry, "/odom", self.odom_callback, 1)
        self.sub_tf = self.create_subscription(TFMessage, "/tf", self.tf_callback, 1)

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
        
        # กำหนดค่าเริ่มต้นของระบบ
        self.navigation_active = False
        self.mapping_active = False
        self.node_check_counter = 0
        
        # เก็บเวลาเริ่มต้นของแต่ละเซนเซอร์ ให้เป็น None เพื่อป้องกัน Stale Data
        self.last_scan_time = None
        self.last_imu_time = None
        self.last_odom_time = None
        self.last_tf_time = None

        self.get_logger().info("ROS2GO Monitor Node started (Optimized Version).")

    # --- Callbacks สำหรับอัปเดตเวลาล่าสุดที่ได้รับข้อมูล ---
    # 👉 ใช้ time.time() ประหยัด CPU กว่า self.get_clock().now() อย่างมหาศาล
    def scan_callback(self, msg):
        self.last_scan_time = time.time()

    def imu_callback(self, msg):
        self.last_imu_time = time.time()

    def odom_callback(self, msg):
        self.last_odom_time = time.time()

    def tf_callback(self, msg):
        self.last_tf_time = time.time()

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
        now = time.time()

        # 1. เช็ค Mapping/Navigation mode จาก Node List 
        # 👉 ปรับเป็นทุกๆ 10 วินาที เพื่อให้ประหยัดทรัพยากรขั้นสุด
        self.node_check_counter += 1
        if self.node_check_counter >= 10:
            node_names = self.get_node_names()
            self.mapping_active = any('slam_toolbox' in str(name).lower() for name in node_names)
            self.navigation_active = any('bt_navigator' in str(name).lower() for name in node_names)
            self.node_check_counter = 0
            
        # 2. เช็ค Sensor Status 
        # 👉 โค้ดส่วนคำนวณเวลาสั้นและเร็วกว่าเดิมมาก เพราะไม่ได้ใช้ ROS 2 Time Object
        time_since_scan = (now - self.last_scan_time) if self.last_scan_time else 999.0
        time_since_imu = (now - self.last_imu_time) if self.last_imu_time else 999.0
        time_since_odom = (now - self.last_odom_time) if self.last_odom_time else 999.0
        time_since_tf = (now - self.last_tf_time) if self.last_tf_time else 999.0

        lidar_ok = time_since_scan < 3.0
        imu_ok = time_since_imu < 3.0
        odom_ok = time_since_odom < 3.0
        tf_ok = time_since_tf < 3.0

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
