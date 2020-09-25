# top level module for sk8

import monad   # globals
import cortex
import portal
import eyes
import wheels

monad.eyes = eyes.Eyes()   # fly the drone, recv video & telemetry, maintain map
monad.wheels = wheels.Wheels()  # drive the skateboard via the arduino
monad.cortex = cortex.Cortex()  # read map, plot route
monad.portal = portal.Portal()  # webserver, human interface

monad.cortex.command('wakeup')
