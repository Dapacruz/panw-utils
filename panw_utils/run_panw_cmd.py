#!/usr/bin/env python3

'''Execute CLI commands

run_panw_cmd.py

Author: David Cruz (davidcruz72@gmail.com)

Python version >= 3.6

Required Python packages:
    Netmiko

Features:
    Executes arbitrary CLI commands
    Command line options
    Platform independent
    Save key based auth preference, default user and default firewall
    Update saved settings
    Multi-threaded
'''

import argparse
from getpass import getpass
import json
from netmiko import ConnectHandler
import os
import os.path
import queue
import signal
import sys
import threading

print_queue = queue.Queue()


def sigint_handler(signum, frame):
    sys.exit(1)


def parse_args():
    parser = argparse.ArgumentParser(description='Executes arbitrary CLI commands')
    parser.add_argument('firewalls', type=str, nargs='*', help='Space separated list of firewalls to query')
    parser.add_argument('-c', '--command', type=str, action='append', help='CLI command to execute (can be used multiple times)')
    parser.add_argument('-U', '--update', action='store_true', help='Update saved settings')
    parser.add_argument('-g', '--global-delay-factor', metavar='', type=int, default=1, help='Increase wait time for prompt (default is 1)')
    parser.add_argument('-u', '--user', metavar='', type=str, help='User')
    parser.add_argument('-p', '--password', metavar='', type=str, help='Password')
    parser.add_argument('-K', '--key-based-auth', action='store_true', help='Use key based authentication')
    return parser.parse_args()


def import_saved_settings(settings_path):
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
            'key': input('API Key: '),
        }
        with open(settings_path, 'w') as f:
            json.dump(settings, f, sort_keys=True, indent=2)
        os.chmod(settings_path, 0o600)

    return settings


def update_saved_settings(settings, settings_path):
    print('\nUpdating saved settings ...\n')
    settings['default_firewall'] = input(f'New Default Firewall [{settings["default_firewall"]}]: ') or settings['default_firewall']
    settings['default_user'] = input(f'New Default User [{settings["default_user"]}]: ') or settings['default_user']
    with open(settings_path, 'w') as f:
        json.dump(settings, f, sort_keys=True, indent=2)
    print('\nSettings updated!')


def connect_ssh(args, settings, key_path, host):
    panos = {
        'host': host,
        'device_type': 'paloalto_panos',
        'username': args.user,
        'password': args.password,
        'global_delay_factor': args.global_delay_factor,
    }

    if not args.user:
        panos['username'] = settings['default_user']

    if args.key_based_auth:
        panos['key_file'] = key_path
        panos['use_keys'] = True

    try:
        net_connect = ConnectHandler(**panos)
        output = []
        for cmd in args.command:
            output.append(f'=== {cmd} ===')
            output.append('\n'.join(net_connect.send_command(cmd).split('\n')[1:]))
    except Exception as e:
        sys.stderr.write(f'Connection error: {e}')
        sys.exit(1)
    finally:
        net_connect.disconnect()

    print_output(output, host)


def print_output(output, host):
    print_queue.put([
        f'{"=" * (len(host) + 4)}',
        f'= {host} =',
        f'{"=" * (len(host) + 4)}',
        *output,
        '\n',
    ])


def print_manager():
    while True:
        job = print_queue.get()
        for line in job:
            print(line)
        print_queue.task_done()


def main():
    # Ctrl+C graceful exit
    signal.signal(signal.SIGINT, sigint_handler)

    args = parse_args()

    if os.environ.get('USERPROFILE'):
        settings_path = os.path.join(os.environ.get('USERPROFILE'), '.panw-settings.json')
        key_path = os.path.join(os.environ.get('USERPROFILE'), '.ssh', 'id_rsa')
    else:
        settings_path = os.path.join(os.environ.get('HOME'), '.panw-settings.json')
        key_path = os.path.join(os.environ.get('HOME'), '.ssh', 'id_rsa')
    settings = import_saved_settings(settings_path)

    if args.update:
        update_saved_settings(settings, settings_path)
        sys.exit(0)

    # Receive firewalls from stdin
    if not sys.stdin.isatty():
        args.firewalls = [i.strip() for i in sys.stdin]
        # Remove empty strings (Windows PowerShell Select-String cmdlet issue)
        args.firewalls = list(filter(None, args.firewalls))

    if not args.firewalls:
        args.firewalls = [settings['default_firewall']]
    if not args.user:
        args.user = settings['default_user']
    if not args.key_based_auth and not args.password:
        args.password = getpass(f"Password ({args.user}): ")

    # Start print manager
    t = threading.Thread(target=print_manager)
    t.daemon = True
    t.start()
    del t

    # Execute CLI commands and print output
    print('Connecting via SSH ...', file=sys.stderr)
    worker_threads = []
    for host in args.firewalls:
        t = threading.Thread(target=connect_ssh, args=(args, settings, key_path, host))
        worker_threads.append(t)
        t.start()

    for t in worker_threads:
        t.join()

    print_queue.join()

    sys.exit(0)


if __name__ == '__main__':
    main()
