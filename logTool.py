#!/usr/bin/env python3

import argparse

parser = argparse.ArgumentParser(description="A log tool to assist debugging.")

# specifying the command line arguments that the program is willing to accept
parser.add_argument(
    "-n", "--name", choices=['fed-amf'], help="name of the federation")
parser.add_argument("-p", "--pod", help="name of the pod")
parser.add_argument("-c", "--container", help="name of the container")

# parse_args() method returns actual argument data from the command line
args = parser.parse_args()

# perform some action only if -n value specified
if args.name == 'fed-amf':
    print("Welcome to fed-amf.")

    # if pod name and container name OR only pod name specified, use database to store information.
    if args.pod and args.container:
        print(args.pod, args.container)
    elif args.pod:
        print(args.pod)
    # if pod name is not specified but container name is, then ignore container name.
    elif args.pod == None and args.container:
        print(
            f"Please enter a pod name to access {args.container}. Ignoring container argument. ")

print("Thanks for using AMFCC's log tool.")
