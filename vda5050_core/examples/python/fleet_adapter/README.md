# VDA5050 Python Fleet Adapter Example

The C++ core, exposed to Python as `vda5050_core_python`, handles the common
VDA5050 behaviour, including:

* connecting to the MQTT broker;
* receiving and validating VDA5050 orders;
* dispatching route nodes in sequence;
* publishing robot state.

Robot-specific behaviour is implemented in `RobotClientAPI.py`.

The provided implementation is a print-only robot, so no real robot or
simulator is required. It prints each received command, waits for a configured
travel time, updates its position in memory, and reports the command as
completed.

## Files

* `RobotClientAPI.py`: defines how to communicate with the robot, including
  navigation, stopping, actions, position, battery and command completion.
  Edit this file by replacing the code under the `IMPLEMENT YOUR CODE HERE`
  markers.
* `config.yaml`: defines the fleet, robot identity, MQTT broker, starting pose
  and simulated travel time. Edit this for your setup.
* `fleet_adapter.py`: connects `RobotClientAPI.py` to the VDA5050 Python
  bindings. You rarely need to edit this file.
* `publish_demo_order.py`: publishes a demo VDA5050 order for testing. Edit
  this only when changing the test route.

## How It Works

```text
VDA5050 order
    ->
vda5050_core Python bindings
    ->
fleet_adapter.py
    ->
RobotClientAPI.py
    ->
Print-only robot
```

Robot state travels in the opposite direction:

```text
Robot position, battery and command status
    ->
RobotClientAPI.py
    ->
fleet_adapter.py
    ->
vda5050_core
    ->
VDA5050 state topic
```

## Prerequisites

The example requires:

* ROS 2 Jazzy;
* a built `vda5050_core` workspace;
* an MQTT broker such as Mosquitto;
* the Python packages `pyyaml` and `paho-mqtt`.

Install the Python dependencies:

```bash
python3 -m pip install pyyaml paho-mqtt
```

Install Mosquitto and its command-line clients if they are not already
available:

```bash
sudo apt update
sudo apt install mosquitto mosquitto-clients
```

## Build the Workspace

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

Check that the Python module can be imported:

```bash
python3 -c "import vda5050_core_python; print('Import successful')"
```

You normally only need to rebuild after changing the C++ code or Python
bindings.

## Source Each New Terminal

Every new terminal that runs the adapter or imports
`vda5050_core_python` must source both ROS 2 and the built workspace:

```bash
source /opt/ros/jazzy/setup.bash
source <workspace>/install/setup.bash
```

Replace `<workspace>` with the actual path to your workspace.

The Mosquitto broker terminal does not need the ROS 2 environment.

## Run the Example

Use three terminals.

### Terminal 1 - Start the MQTT Broker

```bash
mosquitto -v
```

### Terminal 2 - Start the Fleet Adapter

Source the environment:

```bash
source /opt/ros/jazzy/setup.bash
source <workspace>/install/setup.bash
```

Go to the example directory and run the adapter:

```bash
cd <path-to-vda5050_core>/examples/python/fleet_adapter
python3 fleet_adapter.py -c config.yaml
```

Expected startup output:

```text
Added robot 'robot_1' - order topic: uagv/v2/Manufacturer/S001/order
Fleet adapter running. Press Ctrl+C to stop.
```

### Terminal 3 - Publish a Demo Order

Source the environment:

```bash
source /opt/ros/jazzy/setup.bash
source <workspace>/install/setup.bash
```

Go to the example directory and publish the order:

```bash
cd <path-to-vda5050_core>/examples/python/fleet_adapter
python3 publish_demo_order.py
```

The fleet adapter terminal should print navigation commands similar to:

```text
[robot_1] navigate -> x=2.00 y=0.00 theta=0.00 map='map1' speed_limit=0.0
[robot_1] navigate -> x=2.00 y=3.00 theta=1.57 map='map1' speed_limit=0.0
[robot_1] navigate -> x=5.00 y=3.00 theta=0.00 map='map1' speed_limit=0.0
```

The print-only robot waits for the configured `travel_time` before reporting
each navigation command as completed. After a node is completed, the C++ core
dispatches the next node in the order.

## View the Published Robot State

Run the following command in another terminal:

```bash
mosquitto_sub -v -t 'uagv/v2/Manufacturer/S001/state'
```

The published state may include:

* the current position;
* battery state of charge;
* current order information;
* action and node states;
* driving status, if it is reported by the adapter.

## Configuration

The example reads its settings from `config.yaml`.

```yaml
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

* `name`: name of the fleet;
* `update_rate_hz`: how often the Python update loop checks robot state and
  command completion;
* `robot_state_update_interval`: VDA5050 state update interval passed to the
  C++ core;
* `manufacturer`: VDA5050 manufacturer identifier;
* `serial_number`: VDA5050 robot serial number;
* `interface_name`: first section of the VDA5050 MQTT topic;
* `version`: VDA5050 protocol version;
* `battery_soc`: initial battery state of charge from `0.0` to `1.0`;
* `travel_time`: simulated travel time for each destination;
* `start`: initial map, position and orientation;
* `broker_uri`: address of the MQTT broker;
* `client_id_prefix`: MQTT client identifier used by the adapter.

For this configuration, the VDA5050 order topic is:

```text
uagv/v2/Manufacturer/S001/order
```

The state topic is:

```text
uagv/v2/Manufacturer/S001/state
```

## Adapt the Example to a Real Robot

Most robot-specific changes should be made in `RobotClientAPI.py`.

Replace the print-only code under the `IMPLEMENT YOUR CODE HERE` markers with
calls to the real robot interface.

Possible robot interfaces include:

* REST API;
* WebSocket;
* ROS 2 topics;
* ROS 2 actions;
* Nav2;
* a vendor SDK;
* Gazebo simulation.

## Current Limitations

### Stop Callback

The current C++ core does not connect stop or cancellation events to the
Python stop callback.

The callback and `RobotAPI.stop()` method are included so the integration is
ready when cancellation support is added.

### Sending Another Order

The current experimental core may retain the completed order as the active
order.

If a new order is ignored, restart the adapter before publishing another
order.

Depending on the intended order-update flow, another option is to reuse the
same `orderId` with a higher `orderUpdateId`.

### State Publishing

State messages may be published when the robot state changes or when order
events occur. They may not be published at a perfectly fixed frequency.

### Print-Only Actions

The print-only robot acknowledges actions immediately. A real robot
integration should call `execution.finished()` only after the action has
actually completed.

## Stop the Example

Press Ctrl+C in the fleet adapter terminal.

Expected output:

```text
Stopping fleet adapter...
```

The update thread and VDA5050 MQTT adapter should then shut down cleanly.
