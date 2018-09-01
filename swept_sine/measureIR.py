#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""      WORK IN PROGRESSSSSS

script para obtener la IR de un altavoz en una habitación,
usando swetpsines

Más adelante servirá para automatizar la toma de medidas en varios
puntos.

"""

import sys
import numpy as np
from scipy import signal


from synthSweep import synthSweep
from extractIR  impoet extractIR

T = 5
FS = 48000
f1 = 20.0
f2 = 20000.0
tail = 0
