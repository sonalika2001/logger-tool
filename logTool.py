#!/usr/bin/env python3

import argparse
import subprocess
import os
from pathlib import Path
import tarfile


def archive_files():
    archive_name = 'logs'
    # storing as .tar.gz file, gz is the compression algorithm
    with tarfile.open(archive_name, 'w:gz') as tf:
        # manual addition, can optimize
        tf.add('log-one.txt'), tf.add('log-two.txt')
    print('Archived log files successfully.')


def store_data():
    # write output of different commands to separate files
    with open('log-one.txt', 'w') as f_one:
        processOne = subprocess.run(['ls'], stdout=f_one, text=True)
    with open('log-two.txt', 'w') as f_two:
        processTwo = subprocess.run(['ls', '-l'], stdout=f_two, text=True)
    if processOne.returncode == 0 and processTwo.returncode == 0:
        print('Data stored successfully.')
        archive_files()


def read_args(args):
    # perform some action only if -n value specified
    if args.name == 'fed-amf':
        print("Welcome to fed-amf.")

        # can modularise the following code
        # if pod name and container name OR only pod name specified, use database to store information.
        if args.pod and args.container:
            store_data()
        elif args.pod:
            store_data()
        # if pod name is not specified but container name is, then ignore container name.
        elif args.pod == None and args.container:
            print(
                f"Please enter a pod name to access {args.container}. Ignoring container argument. ")

    print("Thanks for using AMFCC's log tool.")


def main():
    parser = argparse.ArgumentParser(
        description="A log tool to assist debugging.")

    # specifying the command line arguments that the program is willing to accept
    parser.add_argument(
        "-n", "--name", choices=['fed-amf'], help="name of the federation")
    parser.add_argument("-p", "--pod", help="name of the pod")
    parser.add_argument("-c", "--container", help="name of the container")

    # parse_args() method returns actual argument data from the command line
    args = parser.parse_args()
    read_args(args)


if __name__ == "__main__":
    main()
