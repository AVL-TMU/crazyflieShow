#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2019 Bitcraze AB
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
Simple example of a synchronized swarm choreography using the High level
commander.

The swarm takes off and flies a synchronous choreography before landing.
The take-of is relative to the start position but the Goto are absolute.
The sequence contains a list of commands to be executed at each step.

This example is intended to work with any absolute positioning system.
It aims at documenting how to use the High Level Commander together with
the Swarm class to achieve synchronous sequences.
"""
import threading
import time
from collections import namedtuple
from queue import Queue
import math

import cflib.crtp
from cflib.crazyflie.swarm import CachedCfFactory
from cflib.crazyflie.swarm import Swarm

# Time for one step in second
STEP_TIME = 1

# Possible commands, all times are in seconds
Takeoff = namedtuple('Takeoff', ['height', 'time'])
Land = namedtuple('Land', ['time'])
Goto = namedtuple('Goto', ['x', 'y', 'z', 'time'])
# RGB [0-255], Intensity [0.0-1.0]
Ring = namedtuple('Ring', ['r', 'g', 'b', 'intensity', 'time'])

Helix = namedtuple('Helix', ['d', 'z','zf','theta0','circle_period','No_setpoints','time'])
# Reserved for the control loop, do not use in sequence
Quit = namedtuple('Quit', [])

URI0 = 'radio://0/80/2M/E7E7E7E701'
URI1 = 'radio://0/80/2M/E7E7E7E702'
URI2 = 'radio://0/80/2M/E7E7E7E704'
URI3 = 'radio://0/80/2M/E7E7E7E705'
URI4 = 'radio://0/80/2M/E7E7E7E706'
URI5 = 'radio://0/80/2M/E7E7E7E707'
URI6 = 'radio://0/80/2M/E7E7E7E708'
URI7 = 'radio://0/80/2M/E7E7E7E709'
URI8 = 'radio://0/80/2M/E7E7E7E710'

uris = [
    # 'radio://0/10/2M/E7E7E7E701',  # cf_id 0, startup position [-0.5, -0.5]
    # 'radio://0/10/2M/E7E7E7E702',  # cf_id 1, startup position [ 0, 0]
    # 'radio://0/10/2M/E7E7E7E703',  # cf_id 3, startup position [0.5, 0.5]
    # # Add more URIs if you want more copters in the swarm
    URI0,
    URI1,
    URI2,
    URI3,
    URI4,
    URI5,
    URI6,
    URI7,
    URI8,
]

sequence = [
    # Step, CF_id,  action
    (0,    0,      Takeoff(0.5, 2)),
    (0,    2,      Takeoff(0.5, 2)),
    (0,    3,      Takeoff(0.8, 2)),
    (0,    4,      Takeoff(0.8, 2)),

    (1,    1,      Takeoff(1.2, 2)),

    (2,    0,      Goto(-0.4,  -0.4,   0.5, 1)),
    (2,    2,      Goto(0.4,  0.4,   0.5, 1)),
    (2,    3,      Goto(0.9,  -0.9,   0.8, 1)),
    (2,    4,      Goto(-0.9,  0.9,   0.8, 1)),

    (3,    1,      Goto(0,  0,   1.2, 1)),

    (5,    0,      Goto(0.4, -0.4, 0.5, 2)),
    (5,    2,      Goto(-0.4, 0.4, 0.5, 2)),
    (5,    3,      Goto(-0.9, -0.9, 0.8, 2)),
    (5,    4,      Goto(0.9, 0.9, 0.8, 2)),

    (7,    0,      Goto(0.4, 0.4, 0.5, 2)),
    (7,    2,      Goto(-0.4, -0.4, 0.5, 2)),
    (7,    3,      Goto(-0.9, 0.9, 0.8, 2)),
    (7,    4,      Goto(0.9, -0.9, 0.8, 2)),

    (9,    0,      Goto(-0.4, 0.4, 0.5, 2)),
    (9,    2,      Goto(0.4, -0.4, 0.5, 2)),
    (9,    3,      Goto(0.9, 0.9, 0.8, 2)),
    (9,    4,      Goto(-0.9, -0.9, 0.8, 2)),


    (11,   0,      Goto(-0.4, -0.4, 0.5, 2)),
    (11,   2,      Goto(0.4, 0.4, 0.5, 2)),
    (11,   3,      Goto(0.9, -0.9, 0.8, 2)),
    (11,   4,      Goto(-0.9, 0.9, 0.8, 2)),

    (13,   0,      Goto(-0.4, -0.4, 0.5, 3)),
    (13,   2,      Goto(0.4, 0.4, 0.5, 3)),
    (13,   3,      Goto(-0.9, 0.9, 0.8, 3)),
    (13,   4,      Goto(0.9, -0.9, 0.8, 3)),

    (16,   0,      Goto(0, -0.4, 0.5, 2)),
    (16,   1,      Goto(0, 0, 0.5, 2)),
    (16,   2,      Goto(0, 0.4, 0.5, 2)),
    (16,   3,      Goto(0, 0.9, 0.5, 2)),
    (16,   4,      Goto(0, -0.9, 0.5, 2)),

    (18,    0,      Land(2)),
    (18,    2,      Land(2)),
    (18,    3,      Land(2)),
    (18,    4,      Land(2)),

    (18,    5,      Takeoff(0.4, 2)),
    (18,    6,      Takeoff(0.4, 2)),
    (18,    7,      Takeoff(0.4, 2)),
    (18,    8,      Takeoff(0.4, 2)),

    (19,    1,      Goto(0,  0,   1.2, 1)),

    (20,    5,      Helix(1.5, 0.3, 1.3,   0,  10, 30, 3)),
    (20,    6,      Helix(1.5, 0.5, 1.5,   math.pi/2,  10, 30, 3)),
    (20,    7,      Helix(1.5, 0.7, 1.7,   math.pi,  10, 30, 3)),
    (20,    8,      Helix(1.5, 0.9, 1.9,   3*math.pi/2,  10, 30, 3)),

    
    (34,   1,      Goto(0, 0, 0.5, 2)),
    (34,   5,      Goto(0.4, 0, 0.5, 2)),
    (34,   6,      Goto(0.9, 0, 0.5, 2)),
    (34,   7,      Goto(-0.4, 0, 0.5, 2)),
    (34,   8,      Goto(-0.9, 0, 0.5, 2)),



    (36,    1,      Land(2)),
    (36,    5,      Land(2)),
    (36,    6,      Land(2)),
    (36,    7,      Land(2)),
    (36,    8,      Land(2)),

    

]


def activate_high_level_commander(scf):
    scf.cf.param.set_value('commander.enHighLevel', '1')


def activate_mellinger_controller(scf, use_mellinger):
    controller = 1
    if use_mellinger:
        controller = 2
    scf.cf.param.set_value('stabilizer.controller', str(controller))


def set_ring_color(cf, r, g, b, intensity, time):
    cf.param.set_value('ring.fadeTime', str(time))

    r *= intensity
    g *= intensity
    b *= intensity

    color = (int(r) << 16) | (int(g) << 8) | int(b)

    cf.param.set_value('ring.fadeColor', str(color))


def crazyflie_control(scf):
    cf = scf.cf
    control = controlQueues[uris.index(cf.link_uri)]

    activate_mellinger_controller(scf, False)

    commander = scf.cf.high_level_commander

    # Set fade to color effect and reset to Led-ring OFF
    set_ring_color(cf, 0, 0, 0, 0, 0)
    cf.param.set_value('ring.effect', '14')



    while True:
        command = control.get()
        if type(command) is Quit:
            return
        elif type(command) is Takeoff:
            commander.takeoff(command.height, command.time)
        elif type(command) is Land:
            commander.land(0.0, command.time)
        elif type(command) is Goto:
            commander.go_to(command.x, command.y, command.z, 0, command.time)
        elif type(command) is Helix:
            setpoint_period = command.circle_period/command.No_setpoints
            x_setpoint = command.d / 2.0 * math.cos(command.theta0)
            y_setpoint = command.d / 2.0 * math.sin(command.theta0)
            z_setpoint = command.z
            psi_setpoint = command.theta0-math.pi/2.0
            commander.go_to(x_setpoint, y_setpoint, z_setpoint, psi_setpoint, command.time)
            time.sleep(command.time+1)
            for counter in range(1,command.No_setpoints+1):
                x_setpoint = command.d / 2.0 * math.cos(2*math.pi*counter/command.No_setpoints+command.theta0)
                y_setpoint = command.d / 2.0 * math.sin(2*math.pi*counter/command.No_setpoints+command.theta0)
                z_setpoint = command.z + counter/command.No_setpoints * (command.zf-command.z)
                psi_setpoint = command.theta0 + 2*math.pi*counter/command.No_setpoints-math.pi/2.0
                commander.go_to(x_setpoint, y_setpoint, z_setpoint, psi_setpoint, setpoint_period)
                time.sleep(setpoint_period) 
        elif type(command) is Ring:
            set_ring_color(cf, command.r, command.g, command.b,
                           command.intensity, command.time)
            pass
        else:
            print('Warning! unknown command {} for uri {}'.format(command,
                                                                  cf.uri))


def control_thread():
    pointer = 0
    step = 0
    stop = False

    while not stop:
        print('Step {}:'.format(step))
        while sequence[pointer][0] <= step:
            cf_id = sequence[pointer][1]
            command = sequence[pointer][2]

            print(' - Running: {} on {}'.format(command, cf_id))
            controlQueues[cf_id].put(command)
            pointer += 1

            if pointer >= len(sequence):
                print('Reaching the end of the sequence, stopping!')
                stop = True
                break

        step += 1
        time.sleep(STEP_TIME)

    for ctrl in controlQueues:
        ctrl.put(Quit())


if __name__ == '__main__':
    controlQueues = [Queue() for _ in range(len(uris))]

    cflib.crtp.init_drivers()
    factory = CachedCfFactory(rw_cache='./cache')
    with Swarm(uris, factory=factory) as swarm:
        swarm.parallel_safe(activate_high_level_commander)
        swarm.reset_estimators()

        print('Starting sequence!')

        threading.Thread(target=control_thread).start()

        swarm.parallel_safe(crazyflie_control)

        time.sleep(1)
