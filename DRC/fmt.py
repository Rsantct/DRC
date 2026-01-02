#!/usr/bin/env python3

# Copyright (c) Rafael Sánchez

""" This module provides the Fmt class, tha provides some
    nice ANSI formats for printouts formatting.
"""


class Fmt:
    """
    # Some nice ANSI formats for printouts formatting
    # CREDITS: https://github.com/adoxa/ansicon/blob/master/sequences.txt

    0           all attributes off
    1           bold (foreground is intense)
    4           underline (background is intense)
    5           blink (background is intense)
    7           reverse video
    8           concealed (foreground becomes background)
    22          bold off (foreground is not intense)
    24          underline off (background is not intense)
    25          blink off (background is not intense)
    27          normal video
    28          concealed off
    30          foreground black
    31          foreground red
    32          foreground green
    33          foreground yellow
    34          foreground blue
    35          foreground magenta
    36          foreground cyan
    37          foreground white
    38;2;#      foreground based on index (0-255)
    38;5;#;#;#  foreground based on RGB
    39          default foreground (using current intensity)
    40          background black
    41          background red
    42          background green
    43          background yellow
    44          background blue
    45          background magenta
    46          background cyan
    47          background white
    48;2;#      background based on index (0-255)
    48;5;#;#;#  background based on RGB
    49          default background (using current intensity)
    90          foreground bright black
    91          foreground bright red
    92          foreground bright green
    93          foreground bright yellow
    94          foreground bright blue
    95          foreground bright magenta
    96          foreground bright cyan
    97          foreground bright white
    100         background bright black
    101         background bright red
    102         background bright green
    103         background bright yellow
    104         background bright blue
    105         background bright magenta
    106         background bright cyan
    107         background bright white
    """

    BG_YELLOW       = '\033[43m'
    BG_CYAN         = '\033[46m'

    BLACK           = '\033[30m'
    RED             = '\033[31m'
    GREEN           = '\033[32m'
    YELLOW          = '\033[33m'
    BLUE            = '\033[34m'
    MAGENTA         = '\033[35m'
    CYAN            = '\033[36m'
    WHITE           = '\033[37m'
    GRAY            = '\033[90m'

    BRIGHTBLACK     = '\033[90m'
    BRIGHTRED       = '\033[91m'
    BRIGHTGREEN     = '\033[92m'
    BRIGHTYELLOW    = '\033[93m'
    BRIGHTBLUE      = '\033[94m'
    BRIGHTMAGENTA   = '\033[95m'
    BRIGHTCYAN      = '\033[96m'
    BRIGHTWHITE     = '\033[97m'

    BOLD            = '\033[1m'
    UNDERLINE       = '\033[4m'
    BLINK           = '\033[5m'
    END             = '\033[0m'


