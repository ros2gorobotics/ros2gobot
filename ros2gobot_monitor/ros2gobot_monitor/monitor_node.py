#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rcl_interfaces.msg import Log
from ros2gobot_msgs.msg import RobotLog, RobotStatus
from sensor_msgs.msg import LaserScan  # เพิ่มการ import สำหรับเช็ค Lidar
import psutil

class MonitorNode(Node):
    def __init__(self):
        super().__init__("ros2gobot_monitor")

        # ---------------------------------------------------------
        # 1. Subscribers
        # ---------------------------------------------------------
        self.sub_rosout = self.create_subscription(
            Log, "/rosout", self.log_callback, 100
        )
        
        # Subscribe /scan เพื่อเช็ค Lidar Heartbeat
        self.sub_scan = self.create_subscription(
            LaserScan, "/scan", self.scan_callback, 10
        )

        # ---------------------------------------------------------
        # 2. Publishers
        # ---------------------------------------------------------
        self.pub_log = self.create_publisher(RobotLog, "/robot/log", 100)
        self.pub_status = self.create_publisher(RobotStatus, "/robot/status", 10)

        # ---------------------------------------------------------
        # 3. Timers & State Variables
        # ---------------------------------------------------------
        self.timer_status = self.create_timer(1.0, self.status_timer_callback)

        self.battery_level = 100.0
        self.navigation_active = False
        self.mapping_active = False
        
        # Lidar Check
        self.last_scan_time = self.get_clock().now()
        self.lidar_status = "OK"

        self.get_logger().info("ROS2GO Monitor Node started (with Lidar Check).")

    def scan_callback(self, msg):
        """อัปเดตเวลาล่าสุดที่ได้รับข้อมูลจาก Lidar"""
        self.last_scan_time = self.get_clock().now()

    def log_callback(self, msg):
        """จัดการ Log จาก /rosout"""
        if msg.level < 20: return
        
        out_msg = RobotLog()
        out_msg.level = msg.level
        out_msg.node = msg.name
        out_msg.message = msg.msg
        out_msg.stamp = msg.stamp
        
        self.pub_log.publish(out_msg)

    def status_timer_callback(self):
        """ตรวจสอบสถานะระบบทุก 1 วินาที"""
        now = self.get_clock().now()
        
        # 1. เช็ค Mapping/Navigation mode จาก Node List
        node_names = self.get_node_names()
        self.mapping_active = any('slam_toolbox' in name.lower() for name in node_names)
        self.navigation_active = any('bt_navigator' in name.lower() for name in node_names)
        
        # 2. เช็ค Lidar Status
        # ถ้าไม่มีข้อมูล Scan เข้ามาเกิน 3 วินาที ให้ตีความว่า Lidar มีปัญหา
        time_since_scan = (now - self.last_scan_time).nanoseconds / 1e9
        self.lidar_status = "OK" if time_since_scan < 3.0 else "ERROR"

        # สร้างข้อความสถานะ
        status_msg = RobotStatus()
        status_msg.cpu = float(psutil.cpu_percent(interval=None))
        status_msg.ram = float(psutil.virtual_memory().percent)
        status_msg.disk = float(psutil.disk_usage('/').percent)
        
        status_msg.battery = self.battery_level
        status_msg.navigation_active = self.navigation_active
        status_msg.mapping_active = self.mapping_active
        status_msg.lidar_status = self.lidar_status

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
        # เพิ่มเงื่อนไขตรวจสอบสถานะ rclpy ก่อนทำการ shutdown เพื่อป้องกัน Error ซ้ำซ้อน
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == '__main__':
    main()