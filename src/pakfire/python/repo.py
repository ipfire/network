
import os
import ConfigParser as configparser
import urlgrabber

import db as database
from servers import Servers

REPOS_PATH = "/etc/pakfire.repos.d"

class Repositories(object):
    _repositories = []
    
    def __init__(self):
        for file in os.listdir(REPOS_PATH):
            if not file.endswith(".repo"):
                continue
            cp = configparser.ConfigParser()
            cp.read(os.path.join(REPOS_PATH, file))
            for section in cp.sections():
                self._repositories.append(Repository(section, cp.items(section)))

    @property
    def all(self):
        return sorted(self._repositories)
    
    @property
    def enabled(self):
        ret = []
        for r in self._repositories:
            if r.enabled:
                ret.append(r)
        return ret
    
    @property
    def repositories(self):
        return self.enabled

class Repository(object):
    def __init__(self, name, items=None):
        self.name = name

        if items:
            config = {}
            for (key, value) in items:
                config[key] = value
            self.config = config
        
        self.db = database.Database("%s.db" % self.name)
        self.servers = Servers(self.db)
    
    def __cmp__(self, other):
        return cmp(self.name, other.name)
    
    def __str__(self):
        return self.name
    
    def __repr__(self):
        return "<Repository %s>" % self.name
    
    def update_mirrorlist(self, mirrorlist=None):
        if not mirrorlist:
            mirrorlist = self.mirrorlist
        f = urlgrabber.urlopen(mirrorlist)
        for line in f.readlines():
            self.servers.add(line)
        f.close()

    @property
    def enabled(self):
        value = self.config.get("enabled")
        if value == "1":
            return True
        return False

    @property
    def gpgkey(self):
        return self.config.get("gpgkey", None)
    
    @property
    def mirrorlist(self):
        return self.config.get("mirrorlist", None)


if __name__ == "__main__":
    rs = Repositories()
    for r in rs.repositories:
        r.update_mirrorlist()
