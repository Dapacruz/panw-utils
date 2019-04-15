#!/usr/bin/env python3

'''Get firewall interfaces

get-panw-interfaces.py

Author: David Cruz (davidcruz72@gmail.com)

Python version >= 3.6

Required Python packages:
    None

Features:
    Returns a list of firewalls interfaces
    Output can be pasted directly into Excel
    Terse output option for piping to other commands
    Command line options
    Platform independent
    Save API key and default firewall
    Update saved settings
    Override/supply API key on the command line
    Filter on interface properties
    Multi-threaded
'''

import argparse
import json
from collections import namedtuple
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
import xml.dom.minidom as MD
import xml.etree.ElementTree as ET

results = []

print_queue = queue.Queue()
results_queue = queue.Queue()


def sigint_handler(signum, frame):
    sys.exit(1)

def query_api(args, host):
    # Disable certifcate verification
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    # Get connected firewalls
    params = urllib.parse.urlencode({
        'type': 'op',
        'cmd': '<show><interface>all</interface></show>',
        'key': args.key,
    })
    url = f'https://{host}/api/?{params}'

    try:
        with urllib.request.urlopen(url, context=ctx) as response:
            xml = response.read().decode('utf-8')
    except OSError as err:
        sys.stderr.write(f'{host}: Unable to connect to host ({err})\n')
        return

    return xml

def parse_xml(root, host):
    hostname = host
    Interface = namedtuple('Interface', 'hostname ifname state ip')
    results = []
    ifnet = root.findall('./result/ifnet/entry')
    hw = root.findall('./result/hw/entry')
    for l_int in ifnet:
        ifname = l_int.find('name').text
        ip = l_int.find('ip').text
        for p_int in hw:
            if p_int.find('name').text == ifname:
                try:
                    state = p_int.find('state').text
                except AttributeError:
                    state = 'N/A'
        interface = Interface(hostname, ifname, state, ip)
        results.append(interface)
    return results

def print_results(args, results):
    if args.terse:
        regex = re.compile(r'.*?(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}).*$')

    # Print header
    if not args.terse:
        print('\n')
        print(f'{"Firewall" :25}\t{"Interface" :20}\t{"State" :5}\t{"IpAddress" :20}', file=sys.stderr)
        print(f'{"=" * 25 :25}\t{"=" * 20 :20}\t{"=" * 5 :5}\t{"=" * 20 :20}', file=sys.stderr)

    for hostname, ifname, state, ip in results:
        if args.terse:
            try:
                ip = re.match(regex, ip).group(1)
            except AttributeError:
                continue
            if not args.if_state or args.if_state == state:
                print(ip)
        else:
            if not args.if_state or args.if_state == state:
                print(f'{hostname :25}\t{ifname :20}\t{state :5}\t{ip :20}')


def worker(args, host):
    xml = query_api(args, host)

    if args.raw_output:
        print_queue.put(xml.split('\n'))
        return

    try:
        root = ET.fromstring(xml)
    except TypeError as err:
        raise SystemExit(f'Unable to parse XML! ({err})')

    interfaces = parse_xml(root, host)
    sorted_interfaces = sorted(interfaces, key=operator.attrgetter('hostname', 'ifname'))
    results_queue.put(sorted_interfaces)


def print_manager():
    while True:
        job = print_queue.get()
        for line in job:
            print(line)
        print_queue.task_done()


def results_manager():
    global results

    while True:
        result = results_queue.get()
        results += result
        results_queue.task_done()


def main():
    # Ctrl+C graceful exit
    signal.signal(signal.SIGINT, sigint_handler)

    parser = argparse.ArgumentParser(description='Returns a list of firewalls interfaces')
    parser.add_argument('firewalls', type=str, nargs='*', help='Space separated list of firewalls to query')
    parser.add_argument('-k', '--key', metavar='', type=str, help='API key')
    parser.add_argument('-r', '--raw-output', action='store_true', help='Raw XML output')
    parser.add_argument('-t', '--terse', action='store_true', help='Output IP addresses only')
    parser.add_argument('-U', '--update', action='store_true', help='Update saved settings')
    parser.add_argument('--if-state', metavar='', choices=['up', 'down'], help='Filter on interface state')
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
        if not 'key' in settings:
            settings['key'] = input('API Key: ')
            changed = True
        if changed:
            with open(settings_path, 'w') as f:
                json.dump(settings, f, sort_keys=True, indent=2)
    else:
        settings = {
            'default_firewall': input('Default Firewall: '),
            'key': input('API Key: '),
        }
        with open(settings_path, 'w') as f:
            json.dump(settings, f, sort_keys=True, indent=2)
        os.chmod(settings_path, 0o600)

    # Update saved settings
    if args.update:
        print('\nUpdating saved settings ...\n')
        settings['key'] = input(f'New API Key [{settings["key"]}]: ') or settings['key']
        settings['default_firewall'] = input(f'New Default Firewall [{settings["default_firewall"]}]: ') or settings['default_firewall']
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

    if not args.key:
        args.key = settings['key']
    if not args.firewalls:
        args.firewalls = settings['default_firewall']

    # Start print manager
    t = threading.Thread(target=print_manager)
    t.daemon = True
    t.start()
    del t

    # Results manager
    t = threading.Thread(target=results_manager)
    t.daemon = True
    t.start()
    del t

    worker_threads = []
    for host in args.firewalls:
        t = threading.Thread(target=worker, args=(args, host))
        worker_threads.append(t)
        t.start()
    
    for t in worker_threads:
        t.join()

    results_queue.join()
    print_queue.join()

    print_results(args, results)

    sys.exit(0)


if __name__ == '__main__':
    main()
