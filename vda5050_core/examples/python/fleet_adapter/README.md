# VDA5050 Python Fleet Adapter Example

## 1. Overview

This example demonstrates how to build and run a Python fleet adapter using the `vda5050_core_python.rmf_migration` bindings.

It is intended for developers who already have an Open-RMF-style Python robot integration, such as one based on the Open-RMF `fleet_adapter_template`.

The example shows how to reuse an existing robot-specific `RobotAPI` while replacing the Open-RMF fleet-adapter layer with the VDA5050 client adapter.

After migration, robot commands are received from a VDA5050 master through MQTT instead of being dispatched through Open-RMF.

The example demonstrates how to:

- configure a VDA5050 fleet and robot identity
- connect to an MQTT broker
- receive VDA5050 orders and instant actions
- forward navigation, localization and robot-action requests to a Python `RobotAPI`
- report position, battery state and command completion
- run the adapter using `ros2 run`

For a detailed comparison between the Open-RMF and VDA5050 adapter APIs, see the RMF migration guide.

## 2. Architecture

```
VDA5050 master
      |
      | MQTT orders and instant actions
      v
vda5050_core Python bindings
      |
      v
fleet_adapter.py
      |
      v
RobotClientAPI.py
      |
      v
Robot or simulator
```

Robot state flows in the opposite direction:

```
Robot position, battery and command status
      |
      v
RobotClientAPI.py
      |
      v
fleet_adapter.py
      |
      v
vda5050_core
      |
      v
VDA5050 state topic
```



## 3. Files



### `RobotClientAPI.py`

Defines the robot-specific interface used by the adapter, including:

- localization
- navigation
- stopping
- robot-specific actions
- position and map retrieval
- battery-state retrieval
- command-completion checking

Replace the code under the `IMPLEMENT YOUR CODE HERE` markers with calls to the real robot API.

The included implementation is a print-only simulated robot that stores its state in memory, so the example can run without hardware.

### `config.yaml`

Defines:

- fleet name
- MQTT broker
- MQTT client ID
- VDA5050 manufacturer and serial number
- robot starting pose
- battery state
- simulated travel time

Update this file to match your robot and MQTT setup.

### `fleet_adapter.py`

Connects `RobotClientAPI.py` to the `vda5050_core_python.rmf_migration` bindings.

It creates the adapter, registers robots, forwards callbacks, updates robot state and reports command completion.

Most robot-specific communication should be implemented in `RobotClientAPI.py`. Modify `fleet_adapter.py` only when changing callback behaviour or adding custom action handling.

## 4. Prerequisites

The example requires:

- ROS 2 Jazzy
- a built `vda5050_core` workspace
- an MQTT broker such as Mosquitto
- PyYAML



## 5. Steps to run the Example



### 5.1 Build the Workspace

Source ROS 2:

```bash
source /opt/ros/jazzy/setup.bash
```

Go to the workspace root and build the package:

```bash
cd ~/vda5050_core
colcon build --packages-select vda5050_core
```

Source the built workspace:

```bash
source install/setup.bash
```

You normally only need to rebuild after changing the C++ code or Python bindings.

### 5.2 Configure the Fleet and Robot

Open:

```
examples/python/fleet_adapter/config.yaml
```

Example configuration:

```
rmf_fleet:
  name: "demo_fleet"
  update_rate_hz: 5.0
  robot_state_update_interval: 30

  robots:
    robot_1:
      manufacturer: "Manufacturer"
      serial_number: "S001"
      interface_name: "uagv"
      version: "2.0.0"
      battery_soc: 1.0
      travel_time: 2.0

      start:
        map_name: "map1"
        x: 0.0
        y: 0.0
        theta: 0.0

fleet_manager:
  broker_uri: "tcp://localhost:1883"
  client_id_prefix: "demo_fleet_adapter"
```

Important fields:

- `name`: fleet name 
- `update_rate_hz`: frequency of robot-state and completion checks 
- `robot_state_update_interval`: VDA5050 state update interval 
- `manufacturer`: VDA5050 manufacturer identifier 
- `serial_number`: VDA5050 robot serial number 
- `interface_name`: first section of the MQTT topic 
- `version`: VDA5050 protocol version 
- `battery_soc`: initial battery state of charge from `0.0` to `1.0` 
- `travel_time`: simulated travel time for each navigation command 
- `start`: initial map and pose 
- `broker_uri`: MQTT broker address 
- `client_id_prefix`: MQTT client identifier 

For this configuration, the order topic is:

```
uagv/v2/Manufacturer/S001/order
```

The state topic is:

```
uagv/v2/Manufacturer/S001/state
```

### 5.3 Run the terminals

Use three terminals.

### Terminal 1 - Start the MQTT Broker

```bash
mosquitto -v
```

Leave this terminal running.

### Terminal 2 - Run the Fleet Adapter

Source the environment:

```bash
source /opt/ros/jazzy/setup.bash
source <workspace>/install/setup.bash
```

Run the adapter:

```bash
ros2 run vda5050_core fleet_adapter
```

Expected startup output:

```text
Added robot 'robot_1' - order topic: uagv/v2/Manufacturer/S001/order
MQTT client [demo_fleet_adapter] connected to tcp://localhost:1883
Fleet adapter running. Press Ctrl+C to stop.
```

### Terminal 3 - Publish a Test Order

Source the environment:

```bash
source /opt/ros/jazzy/setup.bash
source <workspace>/install/setup.bash
```

Run the example order publisher:

```bash
ros2 run vda5050_core order_publisher
```

The fleet-adapter terminal should print messages similar to:

```text
Accepted new order [test_order]
Dispatching node ID [N0] with sequence [0]
[robot_1] navigate -> x=0.00 y=0.00 theta=0.00 map='map1'

Dispatching node ID [N1] with sequence [2]
[robot_1] navigate -> x=2.00 y=1.00 theta=0.00 map='map1'
```

The print-only robot waits for the configured `travel_time` before reporting each navigation command as completed.

After one node is completed, the VDA5050 core dispatches the next node.

## 6. View the Published Robot State

Run the following command in another terminal:

```bash
mosquitto_sub -v -t 'uagv/v2/Manufacturer/S001/state'
```

The published state may include:

- the current position;
- battery state of charge;
- current order information;
- action and node states;
- driving status, if it is reported by the adapter.

## 7. Adapt the Example to a Real Robot

Most robot-specific changes should be made in `RobotClientAPI.py`.

Replace the print-only implementation under the `IMPLEMENT YOUR CODE HERE` markers with calls to the real robot interface.

Possible interfaces include:

- REST APIs
- WebSockets
- ROS 2 topics
- ROS 2 actions
- Nav2
- vendor SDKs
- Gazebo simulations

The following methods should be connected to the real robot:

```
check_connection()
localize()
navigate()
start_activity()
stop()
position()
battery_soc()
get_map_name()
is_command_completed()
get_data()
```

The adapter should only call `execution.finished()` after the robot has actually completed the navigation or action.

## 8. Stop the Example

Press `Ctrl+C` in the fleet adapter terminal.

Expected output:

```text
Stopping fleet adapter...
```

The update thread and VDA5050 MQTT adapter should then shut down cleanly.