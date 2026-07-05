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
Publish a demo VDA5050 order so the fleet adapter drives its robot.

This stands in for the fleet manager / master. It publishes one order with a
few nodes to the robot's order topic; the running ``fleet_adapter.py`` will
navigate through them in sequence.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import sys
import time

import paho.mqtt.client as mqtt


def build_order(map_id, order_id):
    """Build a simple 3-node route (an L-shaped path)."""
    return {
        'headerId': 1,
        'timestamp': datetime.now(timezone.utc).strftime(
            '%Y-%m-%dT%H:%M:%S.000Z'),
        'version': '2.0.0',
        'manufacturer': 'Manufacturer',
        'serialNumber': 'S001',
        'orderId': order_id,
        'orderUpdateId': 0,
        'nodes': [
            {
                'nodeId': 'node_1', 'sequenceId': 0, 'released': True,
                'actions': [],
                'nodePosition': {'x': 2.0, 'y': 0.0, 'theta': 0.0,
                                 'mapId': map_id},
            },
            {
                'nodeId': 'node_2', 'sequenceId': 2, 'released': True,
                'actions': [],
                'nodePosition': {'x': 2.0, 'y': 3.0, 'theta': 1.57,
                                 'mapId': map_id},
            },
            {
                'nodeId': 'node_3', 'sequenceId': 4, 'released': True,
                'actions': [],
                'nodePosition': {'x': 5.0, 'y': 3.0, 'theta': 0.0,
                                 'mapId': map_id},
            },
        ],
        'edges': [
            {'edgeId': 'edge_1', 'sequenceId': 1, 'released': True,
             'startNodeId': 'node_1', 'endNodeId': 'node_2', 'actions': []},
            {'edgeId': 'edge_2', 'sequenceId': 3, 'released': True,
             'startNodeId': 'node_2', 'endNodeId': 'node_3', 'actions': []},
        ],
    }


def main(argv=None):
    """Publish one demo order to the broker."""
    argv = sys.argv if argv is None else argv
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--broker', default='localhost')
    parser.add_argument('--port', type=int, default=1883)
    parser.add_argument('--map', default='map1', help='map id for node positions')
    parser.add_argument(
        '--topic',
        default='uagv/v2/Manufacturer/S001/order',
        help='VDA5050 order topic',
    )
    parser.add_argument(
        '--order-id', default=None,
        help='order id (default: unique per run so re-runs are not treated '
             'as duplicate orders)',
    )
    args = parser.parse_args(argv[1:])

    order_id = args.order_id or f'demo_order_{int(time.time())}'
    order = build_order(args.map, order_id)
    payload = json.dumps(order)

    client = mqtt.Client()
    client.connect(args.broker, args.port, keepalive=30)
    client.loop_start()
    info = client.publish(args.topic, payload, qos=1)
    info.wait_for_publish()
    client.loop_stop()
    client.disconnect()

    print(f"Published order '{order['orderId']}' "
          f"({len(order['nodes'])} nodes) to {args.topic}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
