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
The RobotAPI class is a wrapper for API calls to the robot.

Here users are expected to fill up the implementations of functions which
will be used by the fleet adapter. For example, if your robot has a REST API,
you will need to make HTTP request calls to the appropriate endpoints within
these functions.

This example fills each function with a dependency-free, print-only robot. It
prints the requested command and keeps the robot's pose in memory, so the
adapter can be run end-to-end without any hardware or simulator.
"""

from __future__ import annotations

import threading
import time


class RobotAPI:
    # The constructor below accepts parameters typically required to submit
    # HTTP requests. Users should modify the constructor as per the
    # requirements of their robot's API
    def __init__(self, config_yaml):
        self.config_yaml = config_yaml
        self.timeout = 5.0
        self.debug = False

        # ---- print-only robot bookkeeping (delete for a real robot) --------
        # In-memory pose/map/battery and one in-flight navigation command per
        # configured robot.
        self._lock = threading.Lock()
        self._robots = {}
        for robot_name, rcfg in config_yaml['rmf_fleet']['robots'].items():
            start = rcfg['start']
            self._robots[robot_name] = {
                'pose': [
                    float(start['x']),
                    float(start['y']),
                    float(start['theta']),
                ],
                'map': start['map_name'],
                'battery_soc': float(rcfg.get('battery_soc', 1.0)),
                'travel_time': float(rcfg.get('travel_time', 2.0)),
                'target': None,       # pose being driven toward, or None
                'arrival_time': 0.0,  # when the fake travel finishes
            }

    def check_connection(self) -> bool:
        """Return True if connection to the robot API server is successful."""
        # ------------------------ #
        # IMPLEMENT YOUR CODE HERE #
        # ------------------------ #
        return True

    def localize(
        self,
        robot_name: str,
        pose,
        map_name: str,
    ) -> bool:
        """Localize the print-only robot at the requested pose."""
        print(
            f'[{robot_name}] localize -> ',
            f'x={pose[0]:.2f} y={pose[1]:.2f} theta={pose[2]:.2f} ',
            f'map={map_name!r}',
            flush=True,
        )
        with self._lock:
            robot = self._robots[robot_name]
            robot['pose'] = [float(pose[0]), float(pose[1]), float(pose[2])]
            robot['map'] = map_name or robot['map']
        return True

    def navigate(
        self,
        robot_name: str,
        pose,
        map_name: str,
        speed_limit=0.0,
    ) -> bool:
        """Request the robot to navigate to pose:[x,y,theta]."""
        # ------------------------ #
        # IMPLEMENT YOUR CODE HERE #
        # ------------------------ #
        print(
            f'[{robot_name}] navigate -> '
            f'x={pose[0]:.2f} y={pose[1]:.2f} theta={pose[2]:.2f} '
            f'map={map_name!r} speed_limit={speed_limit}',
            flush=True,
        )
        with self._lock:
            robot = self._robots[robot_name]
            robot['map'] = map_name or robot['map']
            robot['target'] = [
                float(pose[0]),
                float(pose[1]),
                float(pose[2])
            ]
            robot['arrival_time'] = time.monotonic() + robot['travel_time']
        return True

    def start_activity(
        self,
        robot_name: str,
        activity: str,
        label: str,
    ) -> bool:
        """Request the robot to begin a process."""
        # ------------------------ #
        # IMPLEMENT YOUR CODE HERE #
        # ------------------------ #
        print(
            f'[{robot_name}] start_activity -> '
            f'activity={activity!r} label={label!r}',
            flush=True,
        )
        return True

    def stop(self, robot_name: str) -> bool:
        """Request the robot to stop."""
        # ------------------------ #
        # IMPLEMENT YOUR CODE HERE #
        # ------------------------ #
        # NOTE: the C++ core does not trigger the stop callback yet, so this is
        # not called during a run. It is implemented so the integration is
        # complete once cancel support lands in the adapter.
        print(f'[{robot_name}] stop', flush=True)
        with self._lock:
            self._robots[robot_name]['target'] = None
        return True

    def position(self, robot_name: str) -> list[float]:
        """Return [x, y, theta] expressed in the robot's coordinate frame."""
        # ------------------------ #
        # IMPLEMENT YOUR CODE HERE #
        # ------------------------ #
        with self._lock:
            return list(self._robots[robot_name]['pose'])

    def battery_soc(self, robot_name: str) -> float:
        """Return state of charge of robot as a value between 0.0 and 1.0."""
        # ------------------------ #
        # IMPLEMENT YOUR CODE HERE #
        # ------------------------ #
        with self._lock:
            return self._robots[robot_name]['battery_soc']

    def get_map_name(self, robot_name: str) -> str:
        """Return the name of the map that the robot is currently on."""
        # ------------------------ #
        # IMPLEMENT YOUR CODE HERE #
        # ------------------------ #
        with self._lock:
            return self._robots[robot_name]['map']

    def is_command_completed(self, robot_name: str) -> bool:
        """Return True if the robot has completed its last command."""
        # ------------------------ #
        # IMPLEMENT YOUR CODE HERE #
        # ------------------------ #
        with self._lock:
            robot = self._robots[robot_name]
            if robot['target'] is None:
                return True
            if time.monotonic() >= robot['arrival_time']:
                # Fake travel done: snap the pose to the target.
                robot['pose'] = list(robot['target'])
                robot['target'] = None
                return True
            return False

    def get_data(self, robot_name: str):
        """Return robot update data for the specified robot."""
        with self._lock:
            robot = self._robots.get(robot_name)
            if robot is None:
                return None
            map_name = robot['map']
            position = list(robot['pose'])
            battery_soc = robot['battery_soc']

        if map_name is None or position is None or battery_soc is None:
            return None
        return RobotUpdateData(robot_name, map_name, position, battery_soc)


class RobotUpdateData:
    """Update data for a single robot."""

    def __init__(self,
                 robot_name: str,
                 map_name: str,
                 position: list[float],
                 battery_soc: float):
        self.robot_name = robot_name
        self.position = position
        self.map_name = map_name
        self.battery_soc = battery_soc
