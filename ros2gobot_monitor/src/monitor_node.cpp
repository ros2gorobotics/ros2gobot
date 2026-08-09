#include "ros2gobot_monitor/monitor_node.hpp"

using namespace std::chrono_literals;

MonitorNode::MonitorNode() : Node("ros2gobot_monitor"), node_check_counter_(0)
{
  // 1. Subscribers
  sub_rosout_ = this->create_subscription<rcl_interfaces::msg::Log>(
    "/rosout", 10, std::bind(&MonitorNode::log_callback, this, std::placeholders::_1)
  );

  // 2. Publishers
  pub_log_ = this->create_publisher<ros2gobot_msgs::msg::RobotLog>("/robot/log", 10);
  pub_status_ = this->create_publisher<ros2gobot_msgs::msg::RobotStatus>("/robot/status", 5);

  // 3. Timer (ทำงานทุก 1 วินาที)
  timer_status_ = this->create_wall_timer(
    1.0s, std::bind(&MonitorNode::status_timer_callback, this)
  );

  RCLCPP_INFO(this->get_logger(), "ROS2GO Monitor Node (C++ Standard Structure) started.");
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

float MonitorNode::get_cpu_temp()
{
  std::ifstream thermal_file("/sys/class/thermal/thermal_zone0/temp");
  if (thermal_file.is_open()) {
    std::string temp_str;
    std::getline(thermal_file, temp_str);
    try {
      return std::stof(temp_str) / 1000.0f;
    } catch (...) {
      return 0.0f;
    }
  }
  return 0.0f;
}

float MonitorNode::get_cpu_usage()
{
  // สำหรับความเบา ข้ามการคำนวณ CPU ที่ยุ่งยากไปก่อนให้คืนค่า 0.0
  return 0.0f; 
}

void MonitorNode::status_timer_callback()
{
  // 1. เช็ค Node List ทุกๆ 10 รอบ
  node_check_counter_++;
  if (node_check_counter_ >= 10) {
    auto node_names = this->get_node_names();
    mapping_active_ = false;
    navigation_active_ = false;

    for (const auto & name : node_names) {
      std::string lower_name = name;
      std::transform(lower_name.begin(), lower_name.end(), lower_name.begin(), ::tolower);
      if (lower_name.find("slam_toolbox") != std::string::npos) {
        mapping_active_ = true;
      }
      if (lower_name.find("bt_navigator") != std::string::npos) {
        navigation_active_ = true;
      }
    }
    node_check_counter_ = 0;
  }

  // 2. เช็ค Sensor Status ด้วย count_publishers
  bool lidar_ok = this->count_publishers("/scan") > 0;
  bool imu_ok = this->count_publishers("/imu/data") > 0;
  bool odom_ok = this->count_publishers("/odom") > 0;
  bool tf_ok = this->count_publishers("/tf") > 0;

  // สร้างข้อความ Status
  auto status_msg = ros2gobot_msgs::msg::RobotStatus();
  
  status_msg.cpu_temp = get_cpu_temp();
  status_msg.cpu = 0.0; 
  status_msg.ram = 0.0; 
  status_msg.disk = 0.0;
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
