#!/usr/bin/env python3

'''Get firewall set configuration

get_panw_config_set.py

Author: David Cruz (davidcruz72@gmail.com)

Python version >= 3.6

Required Python packages:
    None

Features:
    Returns the firewall set configuration
    Command line options
    Platform independent
    Save key based auth preference, default SSH user and default firewall
    Update saved settings
'''

import argparse
from getpass import getpass
import json
from collections import namedtuple
import operator
import os
import os.path
from netmiko import ConnectHandler
import re
import signal
import ssl
import sys
import urllib.request
import xml.etree.ElementTree as ET

def sigint_handler(signum, frame):
    sys.exit(1)

def main():
    # Ctrl+C graceful exit
    signal.signal(signal.SIGINT, sigint_handler)

    parser = argparse.ArgumentParser()
    parser.add_argument('firewalls', type=str, nargs='*', help='Space separated list of firewalls to query')
    parser.add_argument('-u', '--user', type=str, help='User')
    parser.add_argument('-p', '--password', type=str, help='Password')
    parser.add_argument('-k', '--key-based-auth', action='store_true', help='Use key based authentication')
    parser.add_argument('-U', '--update', action='store_true', help='Update saved settings')
    args = parser.parse_args()

    if 'USERPROFILE' in os.environ:
        settings_path = os.path.join(os.environ["USERPROFILE"], '.panw-settings.json')
    else:
        settings_path = os.path.join(os.environ["HOME"], '.panw-settings.json')

    # Import saved settings
    if os.path.exists(settings_path):
        with open(settings_path, 'r') as f:
            settings = json.load(f)

        # Check for the existence of settings and add if missing
        changed = False
        if not 'default_firewall' in settings:
            settings['default_firewall'] = input(f'Default Firewall: ')
            changed = True
        if not 'default_user' in settings:
            settings['default_user'] = input('Default User: ')
            changed = True
        if changed:
            with open(settings_path, 'w') as f:
                json.dump(settings, f, sort_keys=True, indent=2)
    else:
        settings = {
            'default_firewall': [input('Default Firewall: ')],
            'default_user': input('Default User: '),
        }
        with open(settings_path, 'w') as f:
            json.dump(settings, f, sort_keys=True, indent=2)
        os.chmod(settings_path, 0o600)

    # Update saved settings
    if args.update:
        print('\nUpdating saved settings ...\n')
        settings['default_firewall'] = input(f'New Default Firewall [{settings["default_firewall"]}]: ') or settings['default_firewall']
        settings['default_user'] = input(f'New Default User [{settings["default_user"]}]: ') or settings['default_user']
        with open(settings_path, 'w') as f:
            json.dump(settings, f, sort_keys=True, indent=2)
        print('\nSettings updated!')
        sys.exit(0)

    # Receive firewalls from stdin
    if not sys.stdin.isatty():
        args.firewalls = [i.strip() for i in sys.stdin]
        # Remove empty strings (Windows PowerShell Select-String cmdlet issue)
        args.firewalls = list(filter(None, args.firewalls))
    elif not args.firewalls:
        args.firewalls = [settings['default_firewall']]

    if not args.user:
        args.key = settings['default_user']

    panos = {
        'device_type': 'paloalto_panos',
        'username': args.user,
        'password': args.password,
    }
    if not panos.get('username'):
        panos['username'] = settings['default_user']
    if not args.key_based_auth:
        panos['password'] = getpass(f"Password ({panos['username']}): ")
    else:
        panos['use_keys'] = True
        
    for host in args.firewalls:
        panos['host'] = host

        try:
            net_connect = ConnectHandler(**panos)
            output = net_connect.send_command('set cli config-output-format set')
            output = net_connect.send_config_set(['show'])
        except Exception as e:
            sys.stderr.write(f'Connection error: {e}')
            sys.exit(1)
        finally:
            net_connect.disconnect()

        # Remove extraneous output
        output = '\n'.join(output.split('\n')[4:-4])
        print(output)

    sys.exit(0)


if __name__ == '__main__':
    main()
