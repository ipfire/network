

class Transactionset(object):
    _packages = []

    def __init__(self):
        pass

    def addPackage(self, package):
        self._packages.append(package)

    def check(self):
        print "Checking Transactionset..."
        for package in self.packages:
            if not package.check():
                return False
        return True

    def install(self, root="/"):
        for package in self.packages:
            package.install(root)

    def resolveDeps(self):
        pass

    def run(self, root="/"):
        print "Running transactionset..."
        if self.check():
            self.install(root)
        else:
            print "Error, when verifying the packages..."

    @property
    def packages(self):
        return sorted(self._packages)
