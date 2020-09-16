#!/usr/bin/env python3

'''Get firewall interfaces

get-panw-interfaces.py

Author: David Cruz (davidcruz72@gmail.com)

Python version >= 3.6

Required Python packages:
    lxml

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
import os
import os.path
import queue
import re
import signal
import ssl
import sys
import threading
import urllib.request
import lxml.etree as ET

results = []

print_queue = queue.Queue()
results_queue = queue.Queue()


def sigint_handler(signum, frame):
    sys.exit(1)


def query_api(host, params):
    # Disable certifcate verification
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    # Get connected firewalls
    params = urllib.parse.urlencode(params)
    url = f'https://{host}/api/?{params}'

    try:
        with urllib.request.urlopen(url, context=ctx) as response:
            xml = response.read().decode('utf-8')
    except OSError as err:
        sys.stderr.write(f'{host}: Unable to connect to host ({err})\n')
        return

    return xml


def parse_interfaces(root, hostname):
    interfaces = {}

    hw = root.findall('./result/hw/entry')
    for int in hw:
        ifname = int.find('name').text
        mac = int.find('mac').text
        status = int.find('st').text

        interfaces[ifname] = {
            'hostname': hostname,
            'mac': mac,
            'status': status
        }

    ifnet = root.findall('./result/ifnet/entry')
    for int in ifnet:
        ifname = int.find('name').text
        ip = int.find('ip').text or 'N/A'
        zone = int.find('zone').text or 'N/A'

        interfaces[ifname] = {
            **interfaces.get(ifname, {}),
            'hostname': hostname,
            'zone': zone,
            'ip': ip
        }

    return interfaces


def parse_interface_config(root, interfaces):
    for ifname, attrs in interfaces.items():
        try:
            attrs['comment'] = root.find(f'./result/network/interface/ethernet/entry[@name="{ifname}"]/comment').text
        except AttributeError:
            attrs['comment'] = ''

        # Check the state of physical interfaces only
        if re.match(r'^ethernet\d+/\d+$', ifname):
            try:
                attrs['state'] = root.find(f'./result/network/interface/ethernet/entry[@name="{ifname}"]/link-state').text
            except AttributeError:
                # Default interface state auto returns nothing
                attrs['state'] = 'auto'
    return interfaces


def parse_interface_vrouter(root, interfaces):
    for ifname, attrs in interfaces.items():
        try:
            vrouter = root.xpath(f'//member[text()="{ifname}"]')[0].getparent().getparent().get('name')
            attrs['vrouter'] = vrouter if vrouter != None else 'N/A'
        except IndexError:
            attrs['vrouter'] = 'N/A'
    return interfaces


def print_results(args, results):
    if args.terse:
        regex = re.compile(r'.*?(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}).*$')

    # Print header
    if not args.terse:
        print('\n')
        print(f'{"Firewall" :25}\t{"Interface" :20}\t{"LinkState" :5}\t{"Status" :24}\t{"MacAddress" :17}\t{"Zone" :17}\t{"IpAddress" :20}\t{"VirtualRouter" :25}\t{"Comment" :25}', file=sys.stderr)
        print(f'{"=" * 25 :25}\t{"=" * 20 :20}\t{"=" * 9 :9}\t{"=" * 24 :24}\t{"=" * 17 :17}\t{"=" * 17 :17}\t{"=" * 20 :20}\t{"=" * 25 :25}\t{"=" * 25 :25}', file=sys.stderr)

    for interfaces in results:
        for ifname, attrs in sorted(interfaces.items()):
            hostname = attrs.get('hostname')
            state = attrs.get('state', 'N/A')
            status = attrs.get('status', 'N/A')
            mac = attrs.get('mac', 'N/A')
            zone = attrs.get('zone', 'N/A')
            ip = attrs.get('ip', 'N/A')
            vrouter = attrs.get('vrouter', 'N/A')
            comment = attrs.get('comment', '')

            if args.terse:
                try:
                    ip = re.match(regex, ip).group(1)
                except AttributeError:
                    continue
                if not args.if_status or args.if_status in status:
                    print(ip)
            else:
                if not args.if_status or args.if_status in status:
                    print(f'{hostname :25}\t{ifname :20}\t{state :9}\t{status :24}\t{mac :17}\t{zone :17}\t{ip :20}\t{vrouter :25}\t{comment :25}')


def worker(args, host):
    url_params = {
        'type': 'op',
        'cmd': '<show><interface>all</interface></show>',
        'key': args.key,
    }
    xml = query_api(host, url_params)

    if args.raw_output:
        print_queue.put(xml.split('\n'))
        return

    try:
        interfaces = parse_interfaces(ET.fromstring(xml), host)
    except TypeError as err:
        raise SystemExit(f'Unable to parse XML! ({err})')

    url_params = {
        'type': 'config',
        'action': 'show',
        'xpath': 'devices/entry/network',
        'key': args.key,
    }
    xml = query_api(host, url_params)
    root = ET.fromstring(xml)

    try:
        interfaces = parse_interface_config(root, interfaces)
    except TypeError as err:
        raise SystemExit(f'Unable to parse XML! ({err})')

    try:
        interfaces = parse_interface_vrouter(root, interfaces)
    except TypeError as err:
        raise SystemExit(f'Unable to parse XML! ({err})')
    results_queue.put(interfaces)


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
        results.append(result)
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
    parser.add_argument('--if-status', metavar='', choices=['up', 'down'], help='Filter on interface state')
    parser.add_argument('--if-state', metavar='', choices=['up', 'down'], help='DEPRECATED: Filter on interface state')
    args = parser.parse_args()

    # Deprecated: Remove args.if_state in the near future
    if args.if_state:
        args.if_status = args.if_state

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
        settings['default_firewall'] = input(
            f'New Default Firewall [{settings["default_firewall"]}]: ') or settings['default_firewall']
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
