#!/usr/bin/env python3
#
# Copyright (C) 2026 ROS-Industrial Consortium Asia Pacific
# Advanced Remanufacturing and Technology Centre
# A*STAR Research Entities (Co. Registration No. 199702110H)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""
VDA5050 fleet adapter following the design pattern of the Open-RMF
``fleet_adapter_template``.
"""

from __future__ import annotations
from ament_index_python.packages import get_package_share_directory

import argparse
import os
import signal
import sys
import threading
import time

import yaml
import vda5050_core_python as vda

from RobotClientAPI import RobotAPI

rmf = vda.rmf_migration


class RobotAdapter:
    """Connects one robot's VDA5050 callbacks to its ``RobotAPI`` methods.

    The callback methods forward commands to ``RobotAPI``. The update loop
    reports state and polls command completion."""

    def __init__(self, name, api):
        self.name = name
        self.api = api
        self.robot_handle = None
        self.execution = None
        self._lock = threading.Lock()

    def make_callbacks(self):
        callbacks = rmf.RobotCallbacks(
            self.navigate,
            self.stop,
            self.execute_action,
        )
        callbacks.localize = self.localize
        return callbacks

    def navigate(self, destination, execution):
        with self._lock:
            self.execution = execution

        x, y = destination.xy
        self.api.navigate(
            self.name,
            [x, y, destination.yaw],
            destination.map,
        )

    def stop(self):
        # The VDA5050 core does not currently invoke this callback.
        self.api.stop(self.name)
        with self._lock:
            self.execution = None
        # TODO: call execution.failed(...) once stop/cancellation
        # support is connected through the core.

    def localize(self, destination, execution):
        """Forward an initPosition request to the robot API."""
        if self.api.localize(
            self.name,
            destination.position,
            destination.map,
        ):
            execution.finished()
        else:
            execution.failed("Robot rejected the localization request")

    def execute_action(
        self,
        action_type,
        action_id,
        execution,
    ):
        self.api.start_activity(
            self.name,
            action_type,
            action_id,
        )
        execution.finished()

    def update(self, state):
        if self.robot_handle is None:
            return

        identifier = rmf.ActivityIdentifier()
        driving = False
        completed_execution = None

        with self._lock:
            execution = self.execution

            if execution is not None:
                if self.api.is_command_completed(self.name):
                    completed_execution = execution
                    self.execution = None
                else:
                    identifier = execution.identifier
                    driving = True

        if completed_execution is not None:
            completed_execution.finished()

        self.robot_handle.update(state, identifier)
        self.robot_handle.more().set_driving(driving)


def build_fleet(config):
    """Create the adapter, fleet and robots from a parsed config dict."""
    fleet_cfg = config['rmf_fleet']
    conn = config['fleet_manager']

    adapter = rmf.Adapter.make()
    fleet_config = rmf.FleetConfiguration(
        fleet_cfg['name'],
        conn['broker_uri'],
        conn['client_id_prefix'],
        int(fleet_cfg.get('robot_state_update_interval', 30)),
    )
    fleet_handle = adapter.add_vda5050_fleet(fleet_config)

    api = RobotAPI(config)
    robots = {}
    for robot_name, rcfg in fleet_cfg['robots'].items():
        robot = RobotAdapter(robot_name, api)
        callbacks = robot.make_callbacks()

        start = rcfg['start']
        initial_state = rmf.RobotState(
            start['map_name'],
            [float(start['x']), float(start['y']), float(start['theta'])],
            float(rcfg.get('battery_soc', 1.0)),
        )
        robot_config = rmf.RobotConfiguration(
            rcfg['manufacturer'],
            rcfg['serial_number'],
            rcfg.get('interface_name', 'uagv'),
            rcfg.get('version', '2.0.0'),
        )
        robot.robot_handle = fleet_handle.add_robot(
            robot_name, initial_state, robot_config, callbacks
        )
        robots[robot_name] = robot

        topic = (
            f'{robot_config.interface_name}/v2/'
            f'{robot_config.manufacturer}/'
            f'{robot_config.serial_number}/order'
        )
        print(f"Added robot '{robot_name}' - order topic: {topic}", flush=True)

    return adapter, robots


def main(argv=None):
    """Load the config, build the fleet, and run until interrupted."""
    argv = sys.argv if argv is None else argv
    parser = argparse.ArgumentParser(description='VDA5050 fleet adapter example')
    package_share = get_package_share_directory('vda5050_core')
    default_config = os.path.join(
        package_share,
        'examples',
        'python',
        'fleet_adapter',
        'config.yaml',
    )
    parser.add_argument(
        '-c', '--config_file', default=default_config,
        help='path to config.yaml (default: alongside this script)',
    )
    args = parser.parse_args(argv[1:])

    with open(args.config_file, encoding='utf-8') as config_file:
        config = yaml.safe_load(config_file)

    adapter, robots = build_fleet(config)

    update_rate = float(config['rmf_fleet'].get('update_rate_hz', 2.0))
    period = 1.0 / update_rate if update_rate > 0 else 0.5
    stop_event = threading.Event()

    def update_loop():
        while not stop_event.is_set():
            for robot in robots.values():
                try:
                    data = robot.api.get_data(robot.name)
                    if data is None:
                        continue
                    state = rmf.RobotState(
                        data.map_name, data.position, data.battery_soc
                    )
                    robot.update(state)
                except Exception as exc:
                    print(
                        f'[update] {robot.name}: {exc}',
                        file=sys.stderr,
                        flush=True,
                    )
            stop_event.wait(period)

    def on_shutdown(_signum, _frame):
        stop_event.set()

    signal.signal(signal.SIGINT, on_shutdown)
    signal.signal(signal.SIGTERM, on_shutdown)

    adapter.start()
    updater = threading.Thread(target=update_loop, daemon=True)
    updater.start()
    print('Fleet adapter running. Press Ctrl+C to stop.', flush=True)

    try:
        while not stop_event.is_set():
            time.sleep(0.1)
    finally:
        print('\nStopping fleet adapter...', flush=True)
        stop_event.set()
        updater.join(timeout=2.0)
        adapter.stop()

    return 0


if __name__ == '__main__':
    sys.exit(main())
