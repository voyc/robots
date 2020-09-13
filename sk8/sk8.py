# top level module for sk8

import state   # global state variables
import cortex
import portal
import eyes
import wheels

cortex = cortex.Cortex()  # reads map, chooses route, drives eyes and wheels
eyes = eyes.Eyes()   # flies the tello drone, receives video and telemetry, maintains map
wheels = wheels.Wheels()  # drives the skateboard via the arduino
portal = portal.Portal()  # webserver, provides human interface to start, stop, monitor 
