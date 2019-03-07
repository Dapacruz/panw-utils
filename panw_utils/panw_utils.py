#!/usr/bin/env python3

'''Display available commands

panw-utils.py

Author: David Cruz (davidcruz72@gmail.com)

Python version >= 3.6

Required Python packages:
    None

Features:
    Returns a list of available commands
'''

import signal
import sys

def sigint_handler(signum, frame):
    sys.exit(1)

def main():
    # Ctrl+C graceful exit
    signal.signal(signal.SIGINT, sigint_handler)

    commands = '''
    Palo Alto Networks Utilities

        https://github.com/Dapacruz/panw-utils

        https://pypi.org/project/panw-utils
        

    Available commands:

        panw-utils: Returns a list of available commands

        get-panw-api-key: Returns the current API key, suitable for piping to pbcopy (macOS) or clip.exe (Windows)

        get-panw-firewalls: Returns a list of firewalls including management address and serial number

        get-panw-interfaces: Returns a list of firewall interfaces

        get-panw-config: Returns the firewall configuration
    '''
    print(commands)

    sys.exit(0)


if __name__ == '__main__':
    main()
