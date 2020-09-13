# top level module for sk8

import monad   # globals
import cortex
import portal
import eyes
import wheels

monad.cortex = cortex.Cortex()  # reads map, chooses route, drives eyes and wheels
monad.eyes = eyes.Eyes()   # flies the tello drone, receives video and telemetry, maintains map
monad.wheels = wheels.Wheels()  # drives the skateboard via the arduino
monad.portal = portal.Portal()  # webserver, provides human interface to start, stop, monitor 
