#!/usr/bin/env python3

'''Get firewall configuration

get_panw_config.py

Author: David Cruz (davidcruz72@gmail.com)

Python version >= 3.6

Required Python packages:
    Netmiko

Features:
    Returns the firewall configuration (set/XML format)
    Command line options
    Platform independent
    Save key based auth preference, default user and default firewall
    Update saved settings
    Multi-threaded
'''

import argparse
from getpass import getpass
import json
from collections import namedtuple
from netmiko import ConnectHandler
import operator
import os
import os.path
import queue
import re
import signal
import ssl
import sys
import threading
import urllib.request

print_queue = queue.Queue()


def sigint_handler(signum, frame):
    sys.exit(1)


def parse_args():
    parser = argparse.ArgumentParser(description='Returns the firewall configuration (set/XML format)')
    parser.add_argument('firewalls', type=str, nargs='*', help='Space separated list of firewalls to query')
    parser.add_argument('-U', '--update', action='store_true', help='Update saved settings')
    parser.add_argument('-f', '--format', choices=['xml', 'set'], default='xml', help='Output format')

    group1 = parser.add_argument_group('Set configuration format')
    group1.add_argument('-g', '--global-delay-factor', metavar='', type=int, default=1, help='Increase wait time for prompt (default is 1)')
    group1.add_argument('-u', '--user', metavar='', type=str, help='User')
    group1.add_argument('-p', '--password', metavar='', type=str, help='Password')
    group1.add_argument('-K', '--key-based-auth', action='store_true', help='Use key based authentication')

    group2 = parser.add_argument_group('XML configuration format')
    group2.add_argument('-k', '--key', metavar='', type=str, help='API key')
    group2.add_argument('-x', '--xpath', metavar='', type=str, help='XML XPath')
    group2.add_argument('-t', choices=['running',
                                       'candidate',
                                       'pushed-template',
                                       'pushed-shared-policy',
                                       'merged',
                                       'synced',
                                       'synced-diff'], default='running', help='Config type')
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
        if not 'key' in settings:
            settings['key'] = input('API Key: ')
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
    settings['key'] = input(f'New API Key [{settings["key"]}]: ') or settings['key']
    with open(settings_path, 'w') as f:
        json.dump(settings, f, sort_keys=True, indent=2)
    print('\nSettings updated!')


def query_api(args, host):
    # Disable certifcate verification
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    # Get connected firewalls
    if args.xpath:
        params = urllib.parse.urlencode({
        'xpath': args.xpath,
        'type': 'config',
        'action': 'show',
        'key': args.key,
    })
    else:
        params = urllib.parse.urlencode({
        'type': 'op',
        'cmd': f'<show><config><{args.t}></{args.t}></config></show>',
        'key': args.key,
    })
    url = f'https://{host}/api/?{params}'
    try:
        with urllib.request.urlopen(url, context=ctx) as response:
            xml_config = response.read().decode('utf-8')
    except OSError as err:
        sys.stderr.write(f'{host}: Unable to connect to host ({err})\n')
        return

    print_config(xml_config, host)

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
        set_config = net_connect.send_command('set cli config-output-format set')
        set_config = net_connect.send_config_set(['show'])
    except Exception as e:
        sys.stderr.write(f'Connection error ({host}): {e}')
        sys.exit(1)
    finally:
        net_connect.disconnect()

    # Replace non printable Unicode characters to fix Windows stdout issue
    set_config = str(set_config.encode('utf-8'))

    # Remove extraneous leading/trailing output
    set_config = '\n'.join(set_config.split('\\n')[4:-4])

    print_config(set_config, host)


def print_config(config, host):
    print_queue.put([
        f'{"=" * (len(host) + 4)}',
        f'= {host} =',
        f'{"=" * (len(host) + 4)}',
        config,
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

    if not args.key:
        args.key = settings['key']
    if not args.firewalls:
        args.firewalls = [settings['default_firewall']]
    if not args.user:
        args.user = settings['default_user']
    if args.format == 'set' and not args.key_based_auth and not args.password:
        args.password = getpass(f"Password ({args.user}): ")

    # Start print manager
    t = threading.Thread(target=print_manager)
    t.daemon = True
    t.start()
    del t

    # Collect, process and print configuration
    if args.format == 'xml':
        worker_threads = []
        for host in args.firewalls:
            t = threading.Thread(target=query_api, args=(args, host))
            worker_threads.append(t)
            t.start()
        
        for t in worker_threads:
            t.join()
    elif args.format == 'set':
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
