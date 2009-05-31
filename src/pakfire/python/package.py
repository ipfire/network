#!/usr/bin/python

import hashlib
import os
import subprocess

import io

class Package(object):
    _info = {}

    def __init__(self, archive):
        self.archive = io.CpioArchive(archive)
    
    def check(self):
        print "Checking package %s..." % self.name
        return self.verify()
    
    def extract(self, root="/"):
        if not os.path.exists(root):
            os.makedirs(root)

        lzma = subprocess.Popen(["lzma", "-dc"],
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,)

        cpio = subprocess.Popen(["cpio",
                                 "--quiet",
                                 "--extract",
                                 "--unconditional",
                                 "--make-directories",
                                 "--no-absolute-filenames",],
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                cwd=root)

        BUF = 1024
        file = self.archive["data.img"]

        # Decompress in one big swoop.
        lzma.stdin.write(file)
        lzma.stdin.close()

        lzmaerr = lzma.stderr.read()
        if lzmaerr:
            raise Exception("Decompression error: %s" % lzmaerr)

        while True:
            buf = lzma.stdout.read(BUF)
            if not buf:
                break
            cpio.stdin.write(buf)
        lzma.stdout.close()

        cpioerr = cpio.stderr.read()
        if cpioerr:
            raise Exception("Archiving error: %s" % cpioerr)

    def install(self, root="/"):
        print "Installing %s..." % self.name
        self.extract(root)
    
    def print_info(self):
        ret = ""
        info = (("Name", self.name),
                ("Version", self.version),
                ("Arch", self.arch),
                ("Release", self.release),
                ("Size", self.size),
                ("Summary", self.summary),
                ("URL", self.url),
                ("License", self.license),
                ("Description", self.description))

        for (key, value) in info:
            ret += "%-12s: %s\n" % (key, value,)
        
        if self.verify:
            ret += "%-12s: %s\n" % ("Signature", "OK")
        else:
            ret += "%-12s: %s\n" % ("Signature", "Broken")
        
        return ret
        
    def verify(self):
        hash = hashlib.sha1(self.archive["data.img"]).hexdigest()
        if hash == self.sha1:
            return True
        return False

    @property
    def arch(self):
        return self.info.get("PKG_ARCH", None)

    @property
    def deps(self):
        return self.info.get("PKG_DEPS", None)

    @property
    def description(self):
        return self.info.get("PKG_DESC", None)

    @property
    def group(self):
        return self.info.get("PKG_GROUP", None)

    @property
    def license(self):
        return self.info.get("PKG_LICENSE", None)

    @property
    def name(self):
        return self.info.get("PKG_NAME", None)

    @property
    def info(self):
        if not self._info:
            self._info = {}
            for line in self.archive["info"].split("\n"):
                if not line or line.startswith("#"):
                    continue
                (key, value) = line.split("=")
                self._info[key] = value.strip("\"")
        return self._info

    @property
    def release(self):
        return self.info.get("PKG_REL", None)

    @property
    def sha1(self):
        return self.info.get("PKG_DATA_SHA1", None)

    @property
    def size(self):
        return self.archive.size

    @property
    def summary(self):
        return self.info.get("PKG_SUMMARY", None)

    @property
    def url(self):
        return self.info.get("PKG_URL", None)

    @property
    def version(self):
        return self.info.get("PKG_VER", None)

