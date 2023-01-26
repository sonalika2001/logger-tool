#!/usr/bin/env python3

import argparse
import subprocess
import os
from pathlib import Path
import tarfile
import sys
import calendar
import time
import shutil
from multiprocessing import Lock
import signal

#pod:isCommon
debugCliData = {'amf-cc':False,'amf-n2':False}
exitMessage = "Thanks for using AMF's log collection tool."
tarDir = ''

class LogParser(argparse.ArgumentParser):
    def error(self, message):
        self.print_help()
        #handling errors when invalid arguments are passed.
        if message.startswith('unrecognized arguments'):
            print(f"\n\u001b[31mError: {message}\nPlease enter the arguments from the given choices.\u001b[0m")
        else:
            print(f"\u001b[31{message}\u001b[0m")
        print(exitMessage)
        sys.exit(2)

def signalHandler(signum,frame):
    global tarDir
    tarDir = f'/tmp/fed-amf'
    shutil.rmtree(tarDir)
    print("\nUser interrupt captured. \nCleaning up and exiting...")
    exit()

signal.signal(signal.SIGINT,signalHandler)
signal.signal(signal.SIGTSTP,signalHandler)

def getTimestamp():
    # gmt stores current gmtime
    gmt = time.gmtime()
    # ts stores timestamp
    ts = calendar.timegm(gmt)
    return ts

def archiveItems(fed,parser):
    global tarDir
    ts = getTimestamp()
    archiveName = f'{fed}-Logs_{ts}.tar.gz'
    # storing as .tar.gz file, gz is the compression algorithm
    with tarfile.open(archiveName, 'w:gz') as tf:
        try:
            tf.add(tarDir,arcname=os.path.basename(tarDir))
        except:
            print("\u001b[31mError: Unable to archive files at the moment. Cleaning up and exiting...\u001b[0m")
            shutil.rmtree(tarDir)
            exit()
        print("\u001b[32mArchived log files successfully.\u001b[0m")
    print("Cleaning up...")
    #deletes unempty directories
    shutil.rmtree(tarDir)

def storeDeploymentList(fed):
    global tarDir
    p=subprocess.run(f"/usr/bin/kubectl get deployment -n {fed}| awk '{{print $1}}'",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if p.stderr.decode()!='':
        print(f"\u001b[31m{p.stderr.decode()}")
        print(f"Couldn't retrieve list of pods at the moment. Cleaning up and exiting...\u001b[0m")
        if os.path.exists(tarDir):
            shutil.rmtree(tarDir)
        exit()
    deploymentList = p.stdout.decode().split('\n')
    #deleting header
    del deploymentList[0] , deploymentList[len(deploymentList)-1] 
    return deploymentList 

def getPort(fed,pod):
    global tarDir
    p=subprocess.run(f"/usr/bin/kubectl get deployment -n {fed} {pod} -o yaml | grep containerPort",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if p.stderr.decode()!='':
        print(f"\u001b[31m{p.stderr.decode()}")
        print(f"Couldn't retrieve container port for {pod} at the moment. Cleaning up and exiting...\u001b[0m")
        if os.path.exists(tarDir):
            shutil.rmtree(tarDir)
        exit()
    containerPort = p.stdout.decode()
    for i in containerPort.split():
        if i.isdigit():
            port = i
            break
    return port

def storeLogs(fileName,fed,instance,pod):
    global tarDir
    #create directory
    if os.path.exists(tarDir):
        pass
    else:
        os.makedirs(tarDir)
    #write to file
    with open(f'{tarDir}/{fileName}', 'w') as logfile:
        try:
            subprocess.run(f'/usr/bin/kubectl cp {fed}/{instance}:/tmp/{fileName} /tmp/{fed}/{fileName} -c {pod}',stdout=subprocess.PIPE,shell=True,check=True)
        except subprocess.CalledProcessError as err:
            print(f"\u001b[31m{err}")
            print(f"Couldn't retrieve logs at the moment. Cleaning up and exiting...\u001b[0m")
            if os.path.exists(tarDir):
                shutil.rmtree(tarDir)
            exit()
    try:
        port = getPort(fed,pod)
        subprocess.run(f'/usr/bin/kubectl exec -n {fed} {instance} -c {pod} -ti -- curl -X DELETE http://127.0.0.1:{port}/debug/v1/delete/{fileName}',stdout=subprocess.PIPE,shell=True,check=True)
    except subprocess.CalledProcessError as err:
        print(f"\u001b[31m{err}")
        print(f"Couldn't delete logs from {instance} at the moment. Cleaning up and exiting...\u001b[0m")
        if os.path.exists(tarDir):
            shutil.rmtree(tarDir)
        exit()

def storeDebugLogs(fed,instance,pod,workerNode):
    global tarDir
    #create directory
    if os.path.exists(tarDir):
        pass
    else:
        os.makedirs(tarDir)
    ts = getTimestamp()
    with open(f'{tarDir}/{fed}-{instance}-{workerNode}-debugLogs.txt', 'w') as logfile:
        try:
            subprocess.run(f'/usr/bin/kubectl logs {instance} -n {fed} -c {workerNode}',stdout=logfile,shell=True,check=True)
        except subprocess.CalledProcessError as err:
            print(f"\u001b[31m{err}")
            print(f"Couldn't retrieve logs at the moment. Cleaning up and exiting...\u001b[0m")
            if os.path.exists(tarDir):
                shutil.rmtree(tarDir)
            exit()

def storeDeployment(fed,pod):
    global tarDir
    #create directory
    if os.path.exists(tarDir):
        pass
    else:
        os.makedirs(tarDir)
    ts = getTimestamp()
    with open(f'{tarDir}/{fed}-{pod}-deployment.yaml', 'w') as logfile:
        try:
            subprocess.run(f'/usr/bin/kubectl get deployment -n {fed} {pod} -o yaml',stdout=logfile,shell=True,check=True)
        except subprocess.CalledProcessError as err:
            print(f"\u001b[31m{err}")
            print(f"Couldn't retrieve deployment file at the moment. Cleaning up and exiting...\u001b[0m")
            if os.path.exists(tarDir):
                shutil.rmtree(tarDir)
            exit()

#fetching file name
def getFileName(fed,instance,parser,pod,isCommon=False,isVerbose=False):
    global tarDir
    port = getPort(fed,pod)

    if(isCommon):
        p=subprocess.run(f'/usr/bin/kubectl exec -n {fed} {instance} -c {pod} -ti -- curl -X GET http://127.0.0.1:{port}/debug/v1/logCollect/common',stdout=subprocess.PIPE,shell=True,check=True,stderr=subprocess.PIPE)
        
        if p.stderr.decode()!='':
            print(f"\u001b[31m{p.stderr.decode()}")
            print(f"Couldn't retrieve common logs at the moment. Cleaning up and exiting...\u001b[0m")
            if os.path.exists(tarDir):
                shutil.rmtree(tarDir)
            exit()
        else: 
            fileName = p.stdout.decode()
            storeLogs(fileName,fed,instance,pod)
    elif(isVerbose):
        p=subprocess.run(f'/usr/bin/kubectl exec -n {fed} {instance} -c {pod} -ti -- curl -X GET http://127.0.0.1:{port}/debug/v1/logCollect/verbose',stdout=subprocess.PIPE,shell=True,check=True,stderr=subprocess.PIPE)
        
        if p.stderr.decode()!='':
            print(f"\u001b[31m{p.stderr.decode()}")
            print(f"Couldn't retrieve common logs at the moment. Cleaning up and exiting...\u001b[0m")
            if os.path.exists(tarDir):
                shutil.rmtree(tarDir)
            exit()
        else: 
            fileName = p.stdout.decode()
            storeLogs(fileName,fed,instance,pod)
    else:
        p=subprocess.run(f'/usr/bin/kubectl exec -n {fed} {instance} -c {pod} -ti -- curl -X GET http://127.0.0.1:{port}/debug/v1/logCollect',stdout=subprocess.PIPE,shell=True,check=True,stderr=subprocess.PIPE)
            
        if p.stderr.decode()!='':
            print(f"\u001b[31m{p.stderr.decode()}")
            print(f"Couldn't retrieve logs at the moment. Cleaning up and exiting...\u001b[0m")
            if os.path.exists(tarDir):
                shutil.rmtree(tarDir)
            exit()
        else:
            fileName = p.stdout.decode()
            storeLogs(fileName,fed,instance,pod)

def getWorkerNodes(fed,pod):
    global tarDir
    p=subprocess.run(f"/usr/bin/kubectl get po -o custom-columns=CONTAINER:.spec.containers[*].name -n {fed} | grep {pod}",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if p.stderr.decode()!='':
        print(f"\u001b[31m{p.stderr.decode()}")
        print(f"Couldn't retrieve list of containers for {pod} at the moment. Cleaning up and exiting...\u001b[0m")
        if os.path.exists(tarDir):
            shutil.rmtree(tarDir)
        exit()
    workerNodeList = p.stdout.decode().split('\n')
    if len(workerNodeList)>1:
        del workerNodeList[1:]
    tempString = ' '.join([str(item) for item in workerNodeList])
    workerNodes = tempString.split(',')
    return workerNodes

def storeInstance(fed):
    global tarDir
    #create directory
    if os.path.exists(tarDir):
        pass
    else:
        os.makedirs(tarDir)
    #store information of pods to file
    with open(f'{tarDir}/fed-amf-podsInformation.txt', 'w') as filePtr:
        try:
            subprocess.run(f"/usr/bin/kubectl get po -o custom-columns=POD:.metadata.name,CONTAINER:.spec.containers[*].name,IMAGE:.spec.containers[*].image -n {fed}",stdout=filePtr,shell=True,check=True)
        except subprocess.CalledProcessError as err:
            print(f"\u001b[31m{err}")
            print(f"Couldn't retrieve pods information at the moment. Cleaning up and exiting...\u001b[0m")
            if os.path.exists(tarDir):
                shutil.rmtree(tarDir)
            exit()
    
    p=subprocess.run(f"/usr/bin/kubectl get po -o custom-columns=POD:.metadata.name -n {fed}",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if p.stderr.decode()!='':
        print(f"\u001b[31m{p.stderr.decode()}")
        print(f"Couldn't retrieve list of pods at the moment. Cleaning up and exiting...\u001b[0m")
        if os.path.exists(tarDir):
            shutil.rmtree(tarDir)
        exit()
    podList = p.stdout.decode().split('\n')
    #deleting header
    del podList[0]   
    return podList

#stores instances, iterates through them while calling upon the getFileName() to store the logs and finally calls archiveItems() to tar the files.
def storeLogCaller(podList,fed,parser,pod=None,isVerbose=False):
    global debugCliData
    #iterating through instances
    for instance in podList:
        #if pod value was not entered
        if pod==None:
            #if it is an instance that starts with the given dictionary of prefixes(pods)
            for key in debugCliData.keys():
                if instance.startswith(key):
                    #checking if common configs have already been stored for each pod or not
                    if debugCliData[key]==False:
                        debugCliData[key]=True
                        getFileName(fed,instance,parser,key,True)
                    getFileName(fed,instance,parser,key,False,isVerbose)                        
        else:
            if instance.startswith(pod):
                if debugCliData[pod]==False:
                        debugCliData[pod]=True
                        getFileName(fed,instance,parser,pod,True)
                getFileName(fed,instance,parser,pod,False,isVerbose)
    
    archiveItems(fed,parser)

def storeDebugLogsCaller(podList,workerNodes,fed,pod,worker=None):
    for instance in podList:
        #if pod value was not entered
        if worker==None:
            for workerNode in workerNodes:
                if instance.startswith(pod):
                    storeDebugLogs(fed,instance,pod,workerNode)                      
        else:
            if instance.startswith(pod):
                storeDebugLogs(fed,instance,pod,worker)
    
def readArguments(args,parser):
    #storing fed names
    fedList =[]
    p=subprocess.run("/usr/bin/kubectl get namespaces | awk '{print $1}'",shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if p.stderr.decode()!='':
        print(f"\u001b[31m{p.stderr.decode()}")
        print(f"Couldn't retrieve feds at the moment.\u001b[0m")
        exit()
    fedList = p.stdout.decode().split('\n')
    del fedList[0], fedList[len(fedList)-1]

    # perform some action only if -n value specified correctly
    if args.namespace in fedList:
        print(f"Fed '{args.namespace}' exists in the cluster. Entering execution...")
        #handling feds apart from fed-amf
        if args.namespace != 'fed-amf':
            print(f"\n\u001b[31mError: This tool doesn't provide support for {args.namespace} at the moment.\u001b[0m")
            exit()

        global tarDir
        tarDir = f'/tmp/{args.namespace}'
        podList = storeInstance(args.namespace)
        deploymentList = storeDeploymentList(args.namespace)
        
        if args.onlydebug and not(args.debuglogs):
            print(f"\u001b[31mError: Please specify the pod from {deploymentList} as argument to '-d' if you wish to store debug logs. Cleaning up and Exiting...\u001b[0m")
            if os.path.exists(tarDir):
                shutil.rmtree(tarDir)
            exit()
        #if -d argument has been entered   
        elif args.debuglogs in deploymentList:   
            workerNodes = getWorkerNodes(args.namespace,args.debuglogs)
            if '' in workerNodes:
                print(f"No workerNodes available for {args.debuglogs}, skipping debug logs...") 
            elif args.container:
                if args.container in workerNodes:
                    print(f"Storing debug logs for {args.container} node of {args.debuglogs}...")
                    storeDebugLogsCaller(podList,workerNodes,args.namespace,args.debuglogs,args.container) 
                else:
                    print(f"\u001b[31m Containers present in {args.debuglogs}: {workerNodes}.\nError:{args.container} doesn't exist in {args.debuglogs}. Cleaning up and Exiting...\u001b[0m")
                    if os.path.exists(tarDir):
                        shutil.rmtree(tarDir)
                    exit()
            else:
                print(f"No container was specified for {args.debuglogs}. Storing debug logs for all containers of {args.debuglogs}...")
                storeDebugLogsCaller(podList,workerNodes,args.namespace,args.debuglogs)

            print(f"Storing deployment files for {args.debuglogs}...")
            storeDeployment(args.namespace,args.debuglogs)

        elif args.debuglogs == 'all': 
            print(f"Storing debug logs and deployment files for {deploymentList} in {args.namespace}...")
            for key in deploymentList:
                workerNodes = getWorkerNodes(args.namespace,key)
                if '' in workerNodes:
                    print(f"No workerNodes available for {key}, skipping debug logs...")
                else:
                    storeDebugLogsCaller(podList,workerNodes,args.namespace,key)
                storeDeployment(args.namespace,key)
        elif args.debuglogs!=None:
            print(f"\u001b[31mError:{args.debuglogs} is not supported at the moment. Please specify a pod from {deploymentList} as argument to '-d'. Cleaning up and Exiting...\u001b[0m")
            if os.path.exists(tarDir):
                shutil.rmtree(tarDir)
            exit()
        elif args.debuglogs==None and args.container!=None:
            print(f"\u001b[31mError: Please specify the pod from {deploymentList} as argument to '-d'. Cleaning up and Exiting...\u001b[0m")
            if os.path.exists(tarDir):
                shutil.rmtree(tarDir)
            exit()
        else:
            pass
        if args.onlydebug:
            archiveItems(args.namespace,parser)
        
        if not(args.onlydebug):
            #storing data for particular pod only
            if args.pod:
                if args.pod in debugCliData:
                    print(f"Storing logs for {args.pod}...")
                    storeLogCaller(podList,args.namespace, parser,args.pod,True) if args.verbose else storeLogCaller(podList,args.namespace, parser,args.pod)
                else:
                    print(f"If you wish to debug a specific pod in a fed, please specify the pod from {list(debugCliData.keys())} as argument to '-p'.\n\u001b[31mError: The pod '{args.pod}' doesn't exist in this cluster. Please enter the name of the pod from the above choices. Cleaning up and Exiting...\u001b[0m")
                    if os.path.exists(tarDir):
                        shutil.rmtree(tarDir)
            #storing data for all pods
            else:
                print(f"No pod argument was entered. Storing logs for pods {list(debugCliData.keys())} in {args.namespace}...")
                storeLogCaller(podList,args.namespace,parser,isVerbose=True) if args.verbose else storeLogCaller(podList,args.namespace,parser) 
    else:
        if args.namespace!=None:
            print(f"The name of the federation that you wish to debug must be provided from {fedList} as argument to '-n' in order to run the script.")
            print(f"\u001b[31mError: The fed '{args.namespace}' doesn't exist in this cluster. Please enter the name of the federation from the above choices. Cleaning up and Exiting...\u001b[0m")
            if os.path.exists(tarDir):
                shutil.rmtree(tarDir)
        else:
            print(f"The name of the federation that you wish to debug must be provided from {fedList} as argument to '-n' in order to run the script.")
            print("\u001b[31mError: No federation argument was entered. Please enter the name of the federation from the above choices. Cleaning up and Exiting...\u001b[0m")
            if os.path.exists(tarDir):
                shutil.rmtree(tarDir)
    print(exitMessage)

def checkExecution():
    if os.access(os.path.expanduser("~/.lockfile.vestibular.lock"), os.F_OK):
        #if the lockfile is already there then check the PID number
        #in the lock file
        pidfile = open(os.path.expanduser("~/.lockfile.vestibular.lock"), "r")
        pidfile.seek(0)
        old_pid = pidfile.readline()
        # Now we check the PID from lock file matches to the current
        # process PID
        if os.path.exists("/proc/%s" % old_pid):
                print("\u001b[31mYou already have an instance of the program running.\u001b[0m")
                sys.exit(1)
        else:
                #File is there but the program is not running
                #Removing lock file for old pid as it can be there because of the program last time it was run...
                os.remove(os.path.expanduser("~/.lockfile.vestibular.lock"))

    pidfile = open(os.path.expanduser("~/.lockfile.vestibular.lock"), "w")
    pidfile.write("%s" % os.getpid())
    pidfile.close()

def main():
    #defining parser
    parser = LogParser(formatter_class=argparse.RawDescriptionHelpFormatter,
    description='''\
Automated retrieval and storage of log data to improve debuggability.

This tool helps collect logs from multiple pods/containers across different federations.
At the moment, this tool only provides support for debugCli logs for amf-cc and amf-n2 from the federation fed-amf.

The name of the federation that you wish to debug must be provided as argument to '-n' in order to run the script.
Additionally, if you wish to debug a specific pod in a fed, please specify the pod as argument to '-p'.

This tool also supports collecting debug logs from all pods in the fed, including deployment files. Use the argument '-d' to specify the pod and '-c' if you wish to collect
from a specific container in the pod.

Examples:
    #Collect and store logs of all pods in fed-amf:
    kubectl logCollect -n fed-amf
    
    #Collect and store logs of a specific pod (amf-cc here) in fed-amf:
    kubectl logCollect -n fed-amf -p amf-cc

    #Additionally, collect and store rest api logs + debug logs of a pod in fed-amf:
    kubectl logCollect -n fed-amf -d amf-cc
                        (or)
    kubectl logCollect -n fed-amf -p amf-cc -d amf-cc
    
    #Collect and store debugCli logs + debug logs of a specific container in a pod:
    kubectl logCollect -n fed-amf -d amf-n2 -c infra
                        (or)
    kubectl logCollect -n fed-amf -p amf-cc -d amf-n2 -c infra                

    #Collect and store debugCli logs + debug logs of all pods in fed-amf:
    kubectl logCollect -n fed-amf -d all
                        (or)
    kubectl logCollect -n fed-amf -p amf-cc -d all

    #To store only debug logs w/o debugCli logs, add the --onlydebug flag:
    kubectl logCollect -n fed-amf -d all --onlydebug
                        (or)
    kubectl logCollect -n fed-amf -d amf-cc --onlydebug
    
    #Display help message:
    kubectl logCollect -h
        ''')
    # specifying the command line arguments that the program is willing to accept
    parser.add_argument(
        "-n", "--namespace", help="name of the federation")
    parser.add_argument("-p", "--pod", help="name of the pod")
    parser.add_argument("-d", "--debuglogs",help="option to print debug logs for a pod")
    parser.add_argument("-c", "--container",help="name of the container you wish to print debug logs for")
    parser.add_argument("-v","--verbose", action='store_true', help="increase output verbosity")
    parser.add_argument("--onlydebug",action='store_true', help="store only debug logs w/o debugCli logs")
    # parse_args() method returns actual argument data from the command line
    args = parser.parse_args()
    
    print("Reading arguments...")
    readArguments(args,parser)


if __name__ == "__main__":
    checkExecution()
    main()
    os.remove(os.path.expanduser("~/.lockfile.vestibular.lock"))