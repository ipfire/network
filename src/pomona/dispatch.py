#!/usr/bin/python

from storage import storageInitialize
from storage.partitioning import doAutoPartition

from constants import *
from windows import *

installSteps = [
                ("welcome",       welcomeWindow,),
                ("experimental",  experimentalWindow,),
                ("console",       [ "LanguageWindow", "KeyboardWindow",]),
                ("storage",       storageInitialize,),
                ("partmethod",    partmethodWindow,),
                ("autopartition", autopartitionWindow,),
                #("autopartitionexecute", doAutoPartition,),
                ("partition",     [ "PartitionWindow",]),
                ("bootloader",    bootloaderWindow,),
                ("complete",      finishedWindow,),
               ]


class Dispatcher:
    def __init__(self, installer):
        self.installer = installer

        self.step = None
        self.skipSteps = {}
        self.dir = DISPATCH_FORWARD

    def stepIsDirect(self, step):
        """Takes a step number"""
        if len(installSteps[step]) == 2:
            return True
        else:
            return False

    def stepInSkipList(self, step):
        return False # XXX

    def nextStep(self):
        while self.step <= len(installSteps) or self.step == None:
            if self.step == None:
                self.step = 0
            else:
                self.step += self.dir

            if self.stepInSkipList(self.step):
                continue
            else:
                break

        if self.step == len(installSteps):
            return None
        else:
            return installSteps[self.step]
