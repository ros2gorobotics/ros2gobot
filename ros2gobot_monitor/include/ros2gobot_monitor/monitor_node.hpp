#ifndef ROS2GOBOT_MONITOR__MONITOR_NODE_HPP_
#define ROS2GOBOT_MONITOR__MONITOR_NODE_HPP_

#include <chrono>
#include <memory>
#include <string>
#include <fstream>
#include <algorithm>

#include "rclcpp/rclcpp.hpp"
#include "ros2gobot_msgs/msg/robot_status.hpp"
#include "ros2gobot_msgs/msg/robot_log.hpp"
#include "rcl_interfaces/msg/log.hpp"

class MonitorNode : public rclcpp::Node
{
public:
  MonitorNode();

private:
  void log_callback(const rcl_interfaces::msg::Log::SharedPtr msg);
  float get_cpu_temp();
  float get_cpu_usage();
  void status_timer_callback();

  rclcpp::Subscription<rcl_interfaces::msg::Log>::SharedPtr sub_rosout_;
  rclcpp::Publisher<ros2gobot_msgs::msg::RobotLog>::SharedPtr pub_log_;
  rclcpp::Publisher<ros2gobot_msgs::msg::RobotStatus>::SharedPtr pub_status_;
  rclcpp::TimerBase::SharedPtr timer_status_;

  int node_check_counter_;
  bool navigation_active_;
  bool mapping_active_;
};

#endif  // ROS2GOBOT_MONITOR__MONITOR_NODE_HPP_
