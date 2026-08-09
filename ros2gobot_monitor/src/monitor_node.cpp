// BSD 3-Clause License
//
// Copyright (c) 2026, MT Robotics Limited Partnership
// All rights reserved.
//
// Redistribution and use in source and binary forms, with or without
// modification, are permitted provided that the following conditions are met:
//
// 1. Redistributions of source code must retain the above copyright notice, this
//    list of conditions and the following disclaimer.
//
// 2. Redistributions in binary form must reproduce the above copyright notice,
//    this list of conditions and the following disclaimer in the documentation
//    and/or other materials provided with the distribution.
//
// 3. Neither the name of the copyright holder nor the names of its
//    contributors may be used to endorse or promote products derived from
//    this software without specific prior written permission.
//
// THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
// AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
// IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
// DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
// FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
// DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
// SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
// CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
// OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
// OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

#include "ros2gobot_monitor/monitor_node.hpp"
#include <cstdio>

using namespace std::chrono_literals;

MonitorNode::MonitorNode() : Node("ros2gobot_monitor"), 
  node_check_counter_(0), last_cpu_total_(0), last_cpu_idle_(0)
{
  sub_rosout_ = this->create_subscription<rcl_interfaces::msg::Log>(
    "/rosout", 10, std::bind(&MonitorNode::log_callback, this, std::placeholders::_1)
  );

  pub_log_ = this->create_publisher<ros2gobot_msgs::msg::RobotLog>("/robot/log", 10);
  pub_status_ = this->create_publisher<ros2gobot_msgs::msg::RobotStatus>("/robot/status", 5);

  timer_status_ = this->create_wall_timer(
    1.0s, std::bind(&MonitorNode::status_timer_callback, this)
  );

  RCLCPP_INFO(this->get_logger(), "ROS2GO Monitor Node (C++ Full System Metrics) started.");
}

void MonitorNode::log_callback(const rcl_interfaces::msg::Log::SharedPtr msg)
{
  if (msg->level < 20) return;

  auto out_msg = ros2gobot_msgs::msg::RobotLog();
  out_msg.level = msg->level;
  out_msg.node = msg->name;
  out_msg.message = msg->msg;
  out_msg.stamp = msg->stamp;

  pub_log_->publish(out_msg);
}

// ---------------------------------------------------------
// ฟังก์ชันอ่าน System Resources (แทนที่ psutil)
// ---------------------------------------------------------
float MonitorNode::get_cpu_temp()
{
  std::ifstream thermal_file("/sys/class/thermal/thermal_zone0/temp");
  if (thermal_file.is_open()) {
    std::string temp_str;
    std::getline(thermal_file, temp_str);
    try { return std::stof(temp_str) / 1000.0f; } catch (...) { return 0.0f; }
  }
  return 0.0f;
}

float MonitorNode::get_cpu_usage()
{
  std::ifstream stat_file("/proc/stat");
  if (!stat_file.is_open()) return 0.0f;
  
  std::string line;
  std::getline(stat_file, line);
  
  unsigned long long user, nice, system, idle, iowait, irq, softirq, steal;
  if (sscanf(line.c_str(), "cpu %llu %llu %llu %llu %llu %llu %llu %llu",
             &user, &nice, &system, &idle, &iowait, &irq, &softirq, &steal) < 8) {
    return 0.0f;
  }
  
  unsigned long long idle_all = idle + iowait;
  unsigned long long system_all = system + irq + softirq;
  unsigned long long virt_all = user + nice + steal;
  unsigned long long total = idle_all + system_all + virt_all;
  
  float usage = 0.0f;
  if (last_cpu_total_ != 0) {
    unsigned long long total_diff = total - last_cpu_total_;
    unsigned long long idle_diff = idle_all - last_cpu_idle_;
    if (total_diff > 0) {
      usage = (1.0f - ((float)idle_diff / total_diff)) * 100.0f;
    }
  }
  
  last_cpu_total_ = total;
  last_cpu_idle_ = idle_all;
  return usage;
}

float MonitorNode::get_ram_usage()
{
  std::ifstream meminfo("/proc/meminfo");
  if (!meminfo.is_open()) return 0.0f;
  
  std::string line;
  unsigned long long mem_total = 0, mem_free = 0, mem_available = 0;
  while (std::getline(meminfo, line)) {
    if (line.find("MemTotal:") == 0) sscanf(line.c_str(), "MemTotal: %llu", &mem_total);
    else if (line.find("MemFree:") == 0) sscanf(line.c_str(), "MemFree: %llu", &mem_free);
    else if (line.find("MemAvailable:") == 0) sscanf(line.c_str(), "MemAvailable: %llu", &mem_available);
  }
  
  if (mem_total > 0) {
    unsigned long long used = mem_total - (mem_available > 0 ? mem_available : mem_free);
    return ((float)used / mem_total) * 100.0f;
  }
  return 0.0f;
}

float MonitorNode::get_disk_usage()
{
  struct statvfs stat;
  if (statvfs("/", &stat) != 0) return 0.0f;
  
  unsigned long long total = stat.f_blocks * stat.f_frsize;
  unsigned long long free = stat.f_bfree * stat.f_frsize;
  if (total > 0) {
    return ((float)(total - free) / total) * 100.0f;
  }
  return 0.0f;
}

// ---------------------------------------------------------

void MonitorNode::status_timer_callback()
{
  // 1. เช็ค Node List
  node_check_counter_++;
  if (node_check_counter_ >= 10) {
    auto node_names = this->get_node_names();
    mapping_active_ = false;
    navigation_active_ = false;

    for (const auto & name : node_names) {
      std::string lower_name = name;
      std::transform(lower_name.begin(), lower_name.end(), lower_name.begin(), ::tolower);
      if (lower_name.find("slam_toolbox") != std::string::npos) mapping_active_ = true;
      if (lower_name.find("bt_navigator") != std::string::npos) navigation_active_ = true;
    }
    node_check_counter_ = 0;
  }

  // 2. เช็ค Sensor Status
  bool lidar_ok = this->count_publishers("/scan") > 0;
  bool imu_ok = this->count_publishers("/imu/data") > 0;
  bool odom_ok = this->count_publishers("/odom") > 0;
  bool tf_ok = this->count_publishers("/tf") > 0;

  // 3. สร้างข้อความ Status
  auto status_msg = ros2gobot_msgs::msg::RobotStatus();
  
  status_msg.cpu_temp = get_cpu_temp();
  status_msg.cpu = get_cpu_usage();  // 👉 ดึง % CPU
  status_msg.ram = get_ram_usage();  // 👉 ดึง % RAM
  status_msg.disk = get_disk_usage();// 👉 ดึง % Disk
  status_msg.battery = 100.0;

  status_msg.navigation_active = navigation_active_;
  status_msg.mapping_active = mapping_active_;

  status_msg.lidar_status = lidar_ok;
  status_msg.imu_status = imu_ok;
  status_msg.odom_status = odom_ok;
  status_msg.tf_status = tf_ok;

  status_msg.hardware_status = imu_ok && odom_ok;
  status_msg.localization_status = tf_ok;

  pub_status_->publish(status_msg);
}

int main(int argc, char * argv[])
{
  rclcpp::init(argc, argv);
  auto node = std::make_shared<MonitorNode>();
  rclcpp::spin(node);
  rclcpp::shutdown();
  return 0;
}
