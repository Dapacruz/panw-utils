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
            'Firewall': hostname,
            'MacAddress': mac,
            'Status': status
        }

    ifnet = root.findall('./result/ifnet/entry')
    for int in ifnet:
        ifname = int.find('name').text
        ip = int.find('ip').text or 'N/A'
        zone = int.find('zone').text or 'N/A'
        vsys = int.find("vsys").text
        vsys = f'vsys{int.find("vsys").text}' if vsys != '0' else 'N/A'

        interfaces[ifname] = {
            **interfaces.get(ifname, {}),
            'Firewall': hostname,
            'Zone': zone,
            'IpAddress': ip,
            'vSys': vsys
        }

    return interfaces


def parse_interface_config(root, interfaces):
    for ifname, attrs in interfaces.items():
        try:
            attrs['Comment'] = root.find(f'./result/network/interface/ethernet/entry[@name="{ifname}"]/comment').text
        except AttributeError:
            attrs['Comment'] = ''

        # Collect the link state of physical interfaces only
        if re.match(r'^ethernet\d+/\d+$', ifname):
            try:
                attrs['LinkState'] = root.find(f'./result/network/interface/ethernet/entry[@name="{ifname}"]/link-state').text
            except AttributeError:
                # Default interface state auto returns nothing
                attrs['LinkState'] = 'auto'

        # Collect the aggregate-group
        if re.match(r'^ethernet\d+/\d+$', ifname):
            try:
                attrs['AggGrp'] = root.find(f'./result/network/interface/ethernet/entry[@name="{ifname}"]/aggregate-group').text
            except AttributeError:
                # Default interface state auto returns nothing
                attrs['AggGrp'] = 'N/A'

        try:
            vrouter = root.xpath(f'//member[text()="{ifname}"]')[0].getparent().getparent().get('name')
            attrs['VirtualRouter'] = vrouter if vrouter != None else 'N/A'
        except IndexError:
            attrs['VirtualRouter'] = 'N/A'

    return interfaces


def print_results(args, results):
    if args.terse:
        regex = re.compile(r'.*?(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}).*$')
    else:
        fields = {
            'Firewall': {
                'width': max([ len('Firewall') ] + [ len(attrs.get('Firewall', '')) for int in results for attrs in int.values() ]),
                'na': 'N/A'
            },
            'Interface': {
                'width': max([ len('Interface') ] + [ len(ifname) for i in results for ifname in i.keys() ]),
                'na': 'N/A'
            },
            'LinkState': {
                'width': max([ len('LinkState') ] + [ len(attrs.get('LinkState', '')) for int in results for attrs in int.values() ]),
                'na': 'N/A'
            },
            'Status': {
                'width': max([ len('Status') ] + [ len(attrs.get('Status', '')) for int in results for attrs in int.values() ]),
                'na': 'N/A'
            },
            'MacAddress': {
                'width': max([ len('MacAddress') ] + [ len(attrs.get('MacAddress', '')) for int in results for attrs in int.values() ]),
                'na': 'N/A'
            },
            'AggGrp': {
                'width': max([ len('AggGrp') ] + [ len(attrs.get('AggGrp', '')) for int in results for attrs in int.values() ]),
                'na': 'N/A'
            },
            'Zone': {
                'width': max([ len('Zone') ] + [ len(attrs.get('Zone', '')) for int in results for attrs in int.values() ]),
                'na': 'N/A'
            },
            'IpAddress': {
                'width': max([ len('IpAddress') ] + [ len(attrs.get('IpAddress', '')) for int in results for attrs in int.values() ]),
                'na': 'N/A'
            },
            'vSys': {
                'width': max([ len('vSys') ] + [ len(attrs.get('vSys', '')) for int in results for attrs in int.values() ]),
                'na': 'N/A'
            },
            'VirtualRouter': {
                'width': max([ len('VirtualRouter') ] + [ len(attrs.get('VirtualRouter', '')) for int in results for attrs in int.values() ]),
                'na': 'N/A'
            },
            'Comment': {
                'width': max([ len('Comment') ] + [ len(attrs.get('Comment', '')) for int in results for attrs in int.values() ]),
                'na': ''
            },
        }

        # Print header
        header = ''
        hr = ''
        first_iter = True
        for field, attrs in fields.items():
            if not first_iter:
                header += '\t'
                hr += '\t'
            else:
                first_iter = False
            header += f'{field :<{attrs["width"]}}'
            hr += f'{("=" * attrs["width"]) :<{attrs["width"]}}'

        print('\n')
        print(header, file=sys.stderr)
        print(hr, file=sys.stderr)

    # Print interfaces info
    for interfaces in results:
        for ifname, if_attrs in sorted(interfaces.items()):
            if_status = if_attrs.get('Status', 'N/A')
            if args.terse:
                try:
                    ip = re.match(regex, if_attrs.get('IpAddress', '')).group(1)
                except AttributeError:
                    continue

                if not args.if_status or args.if_status in if_status:
                    print(ip)
            else:
                if not args.if_status or args.if_status in if_status:
                    line = ''
                    first_iter = True
                    for field in fields.keys():
                        if not first_iter:
                            line += '\t'
                        else:
                            first_iter = False

                        if field == 'Interface':
                            line += f'{ifname :<{fields["Interface"]["width"]}}'
                            continue

                        attr = if_attrs.get(field, fields[field]["na"])
                        line += f'{attr :<{fields[field]["width"]}}'

                    print(line)


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

    # Parse interface operational information
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

    # Parse interface configuration
    try:
        interfaces = parse_interface_config(root, interfaces)
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
