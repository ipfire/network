import isys
from constants import *

from snack import *

from pyfire.translate import _, N_

from urlparse import urlparse, urlunparse, urljoin

class SourceTypeWindow:
    def __call__(self, screen, pomona):
        self.pomona = pomona

        ## If we go backwards we umount
        #  our currently mounted media
        #  and reset the method
        if pomona.dir == DISPATCH_BACK:
            pomona.method.umountMedia()
            pomona.method = None

        while 1:
            g = GridFormHelp(screen, _("Source Type"), "source", 1, 6)

            txt = TextboxReflowed(65, _("In installation you have to choose "
                                                                                                                            "a source for the installation files. "
                                                                                                                            "Mostly you will choose the disc here, "
                                                                                                                            "but you are also able to install by "
                                                                                                                            "HTTP, FTP hard disk or usb-key."))
            g.add(txt, 0, 0, (0, 0, 0, 0))

            options = ((_("Install Disc"), SOURCE_CDROM),
                                                     (_("Internet Source"), SOURCE_URL),
                                                     (_("External Drive"), SOURCE_HD))

            typebox = Listbox(height = len(options), scroll = 0)
            for (txt, val) in options:
                typebox.append(_("%s") % txt, val)

            typebox.setCurrent(SOURCE_CDROM)

            g.add(typebox, 0, 1, (0, 1, 0, 0))

            bb = ButtonBar(screen, [ TEXT_OK_BUTTON, TEXT_BACK_BUTTON ])
            g.add(bb, 0, 5, (0,1,0,0))

            rc = g.run()

            source_type = typebox.current()
            res = bb.buttonPressed(rc)

            screen.popHelpLine()
            screen.popWindow()

            if res == TEXT_BACK_CHECK:
                return INSTALL_BACK

            if source_type == SOURCE_CDROM:
                if not isys.cdromList():
                    ButtonChoiceWindow(screen, _("No CDROM found"),
                            _("You choosed to install from an installtion disc, "
                                    "but there was no cdrom drive found on the system. "
                                    "Please choose another installation method."),
                            buttons = [ TEXT_OK_BUTTON ], width = 50)
                    continue

                from image import CdromInstallMethod
                pomona.method = CdromInstallMethod(pomona.rootPath, pomona.intf)
                break
            elif source_type == SOURCE_URL:
                from urlinstall import UrlInstallMethod
                url = self.geturl(screen, pomona)
                pomona.method = UrlInstallMethod(url, pomona.rootPath, pomona.intf)
                break
            elif source_type == SOURCE_HD:
                from harddrive import HardDriveInstallMethod
                pomona.method = HardDriveInstallMethod(pomona.rootPath, pomona.intf)
                break

        pomona.setBackend()

        return INSTALL_OK

    def geturl(self, screen, pomona):
        toplevel = GridFormHelp(screen, _("Source URL"), "sourceurl", 1, 3)

        toplevel.add(TextboxReflowed(37, _("Enter a host you get the files from."
                                                                                                                                                 "You also must enter a path where the "
                                                                                                                                                 "installer finds the files in."))
                                                                                                                                                , 0, 0, (0, 0, 0, 1))

        host = Entry(24, text = URL_HOST)
        path = Entry(24, text = URL_PATH)
        urlgrid = Grid(2, 2)
        urlgrid.setField(Label(_("Host:")), 0, 0, (0, 0, 1, 0), anchorLeft = 1)
        urlgrid.setField(Label(_("Path:")), 0, 1, (0, 0, 1, 0), anchorLeft = 1)
        urlgrid.setField(host, 1, 0)
        urlgrid.setField(path, 1, 1)
        toplevel.add(urlgrid, 0, 1, (0, 0, 0, 1))

        bb = ButtonBar(screen, (TEXT_OK_BUTTON, TEXT_BACK_BUTTON))
        toplevel.add(bb, 0, 2, growx = 1)

        while 1:
            toplevel.setCurrent(host)
            result = toplevel.run()
            rc = bb.buttonPressed(result)
            if rc == TEXT_BACK_CHECK:
                screen.popWindow()
                return None

            ### Build the URL
            url = urlparse(urljoin(host.value(), path.value()))

            if url.scheme not in ("http", "ftp"):
                ButtonChoiceWindow(screen, _("Wrong Protocol"),
                                                        _("You entered a protocol that is not supported by Pomona. "
                                                                "There are only http:// and ftp:// available."),
                                                        buttons = [ TEXT_OK_BUTTON ], width = 50)
            elif not url.path.endswith("/"):
                ButtonChoiceWindow(screen, _("Syntax Error"),
                                                        _("The path of the URL must end with a /."),
                                                        buttons = [ TEXT_OK_BUTTON ], width = 50)
            else:
                from urlinstall import urlretrieve
                testurl = urljoin(urlunparse(url), INFO_FILE)
                try:
                    urlretrieve(testurl, "/tmp/" + INFO_FILE)
                except IOError, e:
                    ButtonChoiceWindow(screen, _("Error"),
                                                    _("When we tested your given URL there was an error.\n\n%s" % (e,)),
                                                    buttons = [ TEXT_OK_BUTTON ], width = 50)
                    continue
                break

        screen.popWindow()

        return urlunparse(url)
