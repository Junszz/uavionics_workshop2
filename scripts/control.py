#!/usr/bin/python3
import math
import rospy
from std_msgs.msg import Float64
#from geometry_msgs.msg import Twist, Pose
from gazebo_msgs.msg import ModelStates
from tf.transformations import euler_from_quaternion

# to set an default initial state
L = 0.4
R = 0.04
current_velocity = 0.0
current_orientation = 0.0
reference_velocity = 0.0
reference_orientation = 0.0
ROBOTNAME = "uavcar"

def cmd_vel_callback(data):
    #callback function to get the reference cmd_vel from another rosnode
    global reference_velocity
    reference_velocity = data.data


def cmd_orientation_callback(data):
    #callback function to get the reference orientation from another rosnode
    global reference_orientation
    reference_orientation = data.data


def gazebomodelstate_callback(data):
    #callback function to get the current states (velocity, position and etc) of our robot
    global current_velocity, current_orientation, linear_velocity
    robots = data.name
    robot_idx=0

    #in gazebo model state, different "index" represent different robot, thus, we need to find the correspoinding robot index to extract the correct values.
    for idx, robot in enumerate(list(robots)):
        if robot == ROBOTNAME:
            robot_idx = idx
            break
    
    #Then, calculate the linear velocity with Pythagoras' theorem
    linear_velocity = math.sqrt(pow(data.twist[robot_idx].linear.x, 2)+pow(data.twist[robot_idx].linear.y, 2))
    #the orientation is in Quaternion Form, we need to convert it to Euler Form (The one we familiar with) before we proceed
    x_o = data.pose[robot_idx].orientation.x
    y_o = data.pose[robot_idx].orientation.y
    z_o = data.pose[robot_idx].orientation.z
    w = data.pose[robot_idx].orientation.w

    #yaw, rotation along z-axis is the one that we interested, another two should be close to zero all the time
    (roll, pitch, yaw) = euler_from_quaternion([x_o,y_o,z_o,w]) 
    current_orientation = yaw

    # get error that need to be tuned  --> error between reference orientation & current_orientation...
    error = reference_orientation - current_orientation

    # we need to minimize the difference (error) as we have many ways to achieve the specific yaw angle, ex: from 0->90 is the same as 0->-270, but the first one is the better solution
    error = min(error+2*math.pi,error,error-2*math.pi)

    #get the desire angular_velocity to apply to our robot from controller
    angular_velocity = p_controller(error)

    # convert to left & right wheel speed
    left_wheel_speed, right_wheel_speed = convert(reference_velocity, angular_velocity)

    # To publish into L & R motor
    left_wheel_pub.publish(left_wheel_speed)
    right_wheel_pub.publish(right_wheel_speed)


def p_controller(error):
    #a feedback controller which trying to converge the "error" to zero
    gain = 0.6
    return gain*error


def convert(linear_velocity, angular_velocity):
    #differential drive equation
    left_wheel_pub = ((2*linear_velocity) - (angular_velocity*L)) / (2*R)
    right_wheel_pub = ((2*linear_velocity) + (angular_velocity*L)) / (2*R)
    return left_wheel_pub, right_wheel_pub

if __name__ == '__main__':
    # name of this node(controller_system)
    rospy.init_node('controller_system', anonymous=True)

    # subscribe to three nodes ( cmd_vel, cmd_orientation, gazebo_model_state )
    rospy.Subscriber("/cmd_vel", Float64, cmd_vel_callback)
    rospy.Subscriber("/cmd_orientation", Float64, cmd_orientation_callback)
    rospy.Subscriber("/gazebo/model_states", ModelStates,gazebomodelstate_callback)

    # publish to two nodes ( left_wheel_speed, right_wheel_speed )
    left_wheel_pub = rospy.Publisher('/left_wheel_speed', Float64, queue_size=2)
    right_wheel_pub = rospy.Publisher('/right_wheel_speed', Float64, queue_size=2)

    rospy.spin()  # simply keeps python from exiting until this node is stopped