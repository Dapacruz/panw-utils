#!/usr/bin/env python3

'''Get the current API key

get-panw-api-key.py

Author: David Cruz (davidcruz72@gmail.com)

Python version >= 3.6

Required Python packages:
    None

Features:
    Returns the current API key, suitable for piping to pbcopy (macOS) or clip.exe (Windows)
    Command line options
    Platform independent
    Save default user and firewall
    Update saved settings
    Receives pipeline input (stdin)
    Uses a default firewall if one not provided
    Prompts for required parameters if none provided
    Multi-processing
'''

import argparse
from functools import partial
from getpass import getpass
import json
from multiprocessing.pool import ThreadPool as Pool
import os
import signal
import ssl
import sys
import urllib.request
import xml.etree.ElementTree as ET

def sigint_handler(signum, frame):
    sys.exit(1)

def query_api(args, host):
    # Disable certifcate verification
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    # Get connected firewalls
    params = urllib.parse.urlencode({
        'type': 'keygen',
        'user': args.user,
        'password': args.password,
    })
    url = f'https://{host}/api/?{params}'
    try:
        with urllib.request.urlopen(url, context=ctx) as response:
            xml = response.read().decode('utf-8')
    except OSError as err:
        raise SystemExit(f'{host}: Unable to connect to host ({err})')

    return xml, host

def main():
    # Ctrl+C graceful exit
    signal.signal(signal.SIGINT, sigint_handler)

    parser = argparse.ArgumentParser()
    parser.add_argument('hosts', type=str, metavar='', nargs='*', help='Space separated list of firewalls')
    parser.add_argument('-u', '--user', type=str, metavar='', help='API service account username')
    parser.add_argument('-p', '--password', type=str, metavar='', help='API service account password')
    parser.add_argument('-U', '--update', action='store_true', help='Update saved settings')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')
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
            settings['default_user'] = input(f'Default User: ')
            changed = True
        if changed:
            with open(settings_path, 'w') as f:
                json.dump(settings, f, sort_keys=True, indent=2)
    else:
        settings = {
            'default_firewall': input('Default Firewall: '),
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
        args.verbose = True
        if not args.user:
            raise ValueError('The "-u" argument is required when piping to stdin!')
        args.hosts = [i.strip() for i in sys.stdin]
        # Remove empty strings (Windows PowerShell Select-String cmdlet issue)
        args.hosts = list(filter(None, args.hosts))
    elif not args.hosts:
        args.hosts = [settings['default_firewall']]

    if not args.user:
        args.user = settings['default_user']

    if not args.password:
        args.password = getpass(f'Password ({args.user}): ')

    pool = Pool(25)
    for xml, host in pool.imap_unordered(partial(query_api, args), args.hosts):
        # Parse and print the API key
        root = ET.fromstring(xml)
        if args.verbose:
            print(f'{host + ": " :30}', end='')
        try:
            print(root.find(".//key").text)
        except AttributeError as err:
            raise SystemExit(f'Unable to parse API key! ({err})')
        
    sys.exit(0)


if __name__ == '__main__':
    main()
