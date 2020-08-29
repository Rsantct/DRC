#!/usr/bin/env python3

# Copyright (c) 2019 Rafael Sánchez
# This file is part of 'Rsantct.DRC', yet another DRC FIR toolkit.
#
# 'Rsantct.DRC' is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# 'Rsantct.DRC' is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with 'Rsantct.DRC'.  If not, see <https://www.gnu.org/licenses/>.

"""
    This module helps on routing the soundcard LEFT input channel
    towards the convenient loudspeaker channel for testing purposes
    on JACK based audio systems.
"""

import sys
import paramiko
from getpass import getpass, getuser
from time import sleep

########################## CUSTOM JACK PORTS ###############################

jack_dest_L = 'brutefir:in.L'
jack_dest_R = 'brutefir:in.R'

############################################################################

class Remote(object):

    def __init__(self, ip='localhost', user=getuser(), password=''):


        def ssh_connection():

            if not self.ip:
                self.ip       = input("Please enter remote IP: ")
            if not self.user:
                self.user     = input("Please enter remote user name: ")
            if not self.password:
                self.password = getpass(prompt=f"remote JACK server {user}'s password: ")

            cli = paramiko.SSHClient()
            cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            cli.connect(hostname=self.ip, username=self.user, password=self.password)
            c = cli.invoke_shell()
            _ = c.recv(10240)            # flushing welcome message

            return c

        self.ip         = ip
        self.user       = user
        self.password   = password
        self.conn       = ssh_connection()


    def send(self, cmd):

        self.conn.send(f'{cmd}\n'.encode())
        sleep(.1)
        return self.conn.recv(2048).decode()


    def select_channel(self, ch=''):

        me = 'remote_jack.py'

        # disconnect all
        # print(f'({me}) clearing all connections')
        self.send(f'jack_disconnect system:capture_1 {jack_dest_L}')
        self.send(f'jack_disconnect system:capture_1 {jack_dest_R}')
        self.send(f'jack_disconnect system:capture_2 {jack_dest_L}')
        self.send(f'jack_disconnect system:capture_2 {jack_dest_R}')

        if ch.upper() == 'L':
            self.send(f'jack_connect system:capture_1 {jack_dest_L}')
            print(f'({me}) connecting analog L ----> channel L')
        elif ch.upper() == 'R':
            self.send(f'jack_connect system:capture_1 {jack_dest_R}')
            print(f'({me}) connecting analog L ----> channel R')

        return


if __name__ == '__main__':

    try:
        ip   = sys.argv[1]
        user = sys.argv[2]
    except:
        print('demo usage: remotejack.py  <IP>  <username>')
        sys.exit()

    # Running a simple demo
    remote = Remote(ip, user)
    print('running a demo channel selection ...')
    remote.select_channel('L')
    sleep(1)
    remote.select_channel('R')
    sleep(1)
    remote.select_channel('R')
    sleep(1)
    print('bye.')
