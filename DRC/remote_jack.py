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
    This module helps on routing a soundcard input channel (default L)
    towards the convenient loudspeaker channel for testing purposes
    on JACK based audio systems.

    (!) Be aware that you'll need a good network link,
        other ways you may experience delayed responses from remote.

"""

import sys
import paramiko
from getpass import getpass, getuser
from time import sleep
import yaml


try:
    with open(__file__.replace('.py', '.yml'), 'r') as f:
        CFG = yaml.safe_load(f.read())
    in_port = CFG['in']
    lspk_L  = CFG['lspk_L']
    lspk_R  = CFG['lspk_R']

except:
    print(f'(remote_jack) ERROR reading \'remote_jack.yml\' config file')
    in_port = 'system:capture_1'
    lspk_L  = 'brutefir:in.L'
    lspk_R  = 'brutefir:in.R'


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
            return cli

        self.ip         = ip
        self.user       = user
        self.password   = password
        self.cli        = ssh_connection()


    # hiding this class method for safety purposes
    def _run(self, cmd):

        stdin, stdout, stderr = self.cli.exec_command( f'{cmd}\n'.encode(),
                                                       timeout=1 )
        sleep(.1)
        return stdout.read().decode()


    def select_channel(self, ch=''):
        """ selects the destination channel for system:capture_1 (LEFT ANALOG IN)
        """
        # disconnect all
        self._run(f'jack_disconnect system:capture_1 {lspk_L}')
        self._run(f'jack_disconnect system:capture_1 {lspk_R}')
        self._run(f'jack_disconnect system:capture_2 {lspk_L}')
        self._run(f'jack_disconnect system:capture_2 {lspk_R}')
        # connect to channel
        if ch.upper() == 'L':
            self._run(f'jack_connect {in_port} {lspk_L}')
            print(f'(remote_jack) connecting analog {in_port} ----> {lspk_L}')
        elif ch.upper() == 'R':
            self._run(f'jack_connect {in_port} {lspk_R}')
            print(f'(remote_jack) connecting analog {in_port} ----> {lspk_R}')
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
