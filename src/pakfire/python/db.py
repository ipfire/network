

from pysqlite2 import dbapi2 as sqlite

DATABASE_PATH = "."

class Database(object):
    def __init__(self, filename):
        self.filename = filename

        self.connection = sqlite.connect(self.filename)
    
    def add(self, table):
        c = self.cursor
        c.executescript("CREATE TABLE IF NOT EXISTS %s(id, key, value);" % table)
        c.close()

    def commit(self):
        self.connection.commit()

    def destroy(self, table):
        c = self.cursor
        c.execute("DELETE FROM %s" % table)
        c.close()
        self.commit()
    
    def get(self, table, id, key):
        ret = None
        c = self.cursor
        c.execute("SELECT value FROM %s WHERE id='%s' AND key='%s';" % \
                  (table, id, key,))
        try:
            ret = c.fetchone()[0]
        except TypeError:
            pass
        c.close()
        return ret

    def set(self, table, id, key, value):
        c = self.cursor
        if not self.get(id, key):
            c.execute("INSERT INTO %s(id, key, value) VALUES('%s', '%s', '%s');" \
                      % (table, id, key, value,))
        else:
            c.execute("UPDATE %s SET value='%s' WHERE id='%s' AND key='%s';" \
                      % (table, value, id, key,))
        c.close()
        self.commit()

    @property
    def cursor(self):
        return self.connection.cursor()
