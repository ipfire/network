#!/usr/bin/python

import console
import storage
#import timezone

class DataStore:
    def __init__(self, installer):
        self.installer = installer

        self.console  = console.Console(self.installer)
        self.storage  = storage.Storage(self.installer)
        #self.timezone = timezone.Timezone(self.installer)
