
import random
import urlparse
import uuid

SERVER_DEFAULT_PROTOCOL = "http"
SERVER_DEFAULT_PORT = "80"
SERVER_DEFAULT_PATH = ""

class Servers(object):
    table = "servers"

    def __init__(self, db):
        self.db = db
        self.db.add(self.table)
    
    def add(self, url):
        p = urlparse.urlparse(url)
        for server in self.all:
            if str(server) == url:
                return
        server = Server(self.db)
        (server.protocol, server.hostname, server.port, server.path) = \
            (p.scheme, p.hostname, p.port, p.path)

    @property
    def all(self):
        ret = []
        c = self.db.cursor
        c.execute("SELECT DISTINCT id FROM %s" % self.table)
        for id in c.fetchall():
            s = Server(self.db, id)
            ret.append(s)
        return sorted(ret)
    
    @property
    def random(self):
        return random.choice(self.all)


class Server(object):
    table = Servers.table

    def __init__(self, db, id=None):
        self.db = db

        if not id:
            id = str(uuid.uuid4())
        self.id = "%s" % id
    
    def __str__(self):
        return urlparse.urlunparse((self.protocol, \
            "%s:%s" % (self.hostname, self.port), self.path, None, None, None))
    
    def __repr__(self):
        return "<Server %s>" % self.id
    
    def _getHostname(self):
        return self.db.get(self.table, self.id, "hostname")
    
    def _setHostname(self, hostname):
        return self.db.set(self.table, self.id, "hostname", hostname)

    hostname = property(_getHostname, _setHostname)
    
    def _getProtocol(self):
        return self.db.get(self.table, self.id, "protocol") or SERVER_DEFAULT_PROTOCOL
    
    def _setProtocol(self, protocol):
        return self.db.set(self.table, self.id, "protocol", protocol)
    
    protocol = property(_getProtocol, _setProtocol)

    def _getPort(self):
        return self.db.get(self.table, self.id, "port") or SERVER_DEFAULT_PORT
    
    def _setPort(self, port):
        return self.db.set(self.table, self.id, "port", port)

    port = property(_getPort, _setPort)
    
    def _getPath(self):
        return self.db.get(self.table, self.id, "path") or SERVER_DEFAULT_PATH
    
    def _setPath(self, path):
        return self.db.set(self.table, self.id, "path", path)
    
    path = property(_getPath, _setPath)
