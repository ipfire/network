#!/usr/bin/python

from snack import *

import storage.formats as formats

from constants import *

import gettext
_ = lambda x: gettext.ldgettext("pomona", x)

class PartitionWindow(object):
    def populate(self):
        self.lb.clear()

        for vg in self.storage.vgs:
            self.lb.append([vg.name, "", "", "",], None)
            
        for disk in self.storage.disks:
            self.lb.append([disk.path, "", "", "",], None)
            for part in self.storage.partitions:
                if disk == part.disk:
                    mountpoint = type = ""
                    if part.format:
                        type = part.format.name
                        try:
                            mountpoint = part.format.mountpoint
                        except AttributeError:
                            pass
                    self.lb.append(["  %s" % part.name,
                                    mountpoint,
                                    type,
                                    "%dM" % part.size,],
                                    part,
                                    [LEFT, LEFT, LEFT, RIGHT])

    def makeFileSystemList(self, device):
        grid = Grid(1, 2)
        
        label = Label(_("File System type:"))
        grid.setField(label, 0, 0)
        
        fstype = Listbox(height=4, scroll=1)
        for fs in sorted(formats.device_formats.values()):
            if not fs.supported:
                continue
            if fs.formattable:
                fstype.append(fs._type, fs)
        # XXX select default
        #current = formats.device_formats[formats.get_default_filesystem_type()]
        #print current
        #fstype.setCurrent(current)
        ### XXX Callback
        grid.setField(fstype, 0, 1)
        return (grid, fstype)
    
    def makeDriveList(self, device):
        grid = Grid(1, 2)
        
        label = Label(_("Allowable Drives:"))
        grid.setField(label, 0, 0)
        
        drivelist = CheckboxTree(height=4, scroll=1)
        for disk in self.storage.disks:
            drivelist.append(disk.name)
        grid.setField(drivelist, 0, 1)
        return (grid, drivelist)

    def makeMountPoint(self, device):
        grid = Grid(2, 1)
        label = Label(_("Mount Point:"))
        grid.setField(label, 0, 0, (0,0,0,0), anchorLeft = 1)

        try:
            mountpoint = device.format.mountpoint
        except AttributeError:
            mountpoint = ""
        mount = Entry(20, mountpoint)

        grid.setField(mount, 1, 0, anchorRight = 1, growx = 1)

        return (grid, mount)

    def newCb(self):
        choices = [_("Partition"), _("RAID"), _("Logical Volume Group")]

        if self.storage.vgs:
            choices.append(_("Logical Volume Device"))

        (button, choice) = ListboxChoiceWindow(self.installer.intf.screen,
                            _("New device"),
                            _("Which type of device do you want to create?\n\n"),
                            choices, buttons = [TEXT_OK_BUTTON, TEXT_BACK_BUTTON],
                            width = 35, height = len(choices))

        if button == TEXT_BACK_CHECK:
            return

        choice = choices[choice]
        if choice == _("Partition"):
            device = self.storage.newPartition()
        elif choice == _("RAID"):
            device = None # XXX RAID
        elif choice == _("Logical Volume Group"):
            device = self.storage.newVG()
        elif choice == _("Logical Volume Device"):
            device = self.storage.newLV()

        self.edit(device=device)

    def edit(self, device=None):
        if not device:
            return
        
        row = 0
        
        if not device.exists:
            tstr = _("Add Partition")
        else:
            tstr = _("Edit Partition")
        grid = GridForm(self.screen, tstr, 1, 6)
        
        (mountgrid, mountpoint) = self.makeMountPoint(device)
        grid.add(mountgrid, 0, row)
        row += 1
        
        if not device.exists:
            subgrid1 = Grid(2, 1)
            
            (fsgrid, fstype) = self.makeFileSystemList(device)
            subgrid1.setField(fsgrid, 0, 0)
            
            (devgrid, drivelist) = self.makeDriveList(device)
            subgrid1.setField(devgrid, 1, 0, (0,1,0,0), growx=1)
            
            grid.add(subgrid1, 0, row, (0,1,0,0), growx=1)
            row += 1
        
        bb = ButtonBar(self.screen, (TEXT_OK_BUTTON, TEXT_CANCEL_BUTTON))
        grid.add(bb, 0, row, (0,1,0,0), growx = 1)
        row += 1
        
        while 1:
            rc = grid.run()
            button = bb.buttonPressed(rc)

            if button == TEXT_CANCEL_CHECK:
                break

            if mountpoint.value() and not mountpoint.value().startswith("/"):
                self.installer.intf.messageWindow(_("Error"),
                                                  _("Mountpoint must be an absolute path."))
                continue

            if device.format:
                device.format.mountpoint = mountpoint.value()

            break
        
        self.screen.popWindow()
        
    def editCb(self):
        device = self.lb.current()
        if not device:
            self.installer.intf.messageWindow(_("Unable To Edit"),
                                              _("You must first select a partition to edit."))
            return

        self.edit(device)

    def deleteCb(self):
        device = self.lb.current()
        
        if not device:
            self.installer.intf.messageWindow(_("Unable To Delete"),
                                              _("You must first select a partition to delete."))
            return
        
        if not self.installer.intf.messageWindow(_("Confirm Delete"),
                                                 _("Do you really want to delete the selected partition?"),
                                                 type="yesno"):
            return
        
        self.storage.destroyDevice(device)

    def __call__(self, installer):
        self.installer = installer
        self.screen = self.installer.intf.screen
        self.storage = self.installer.ds.storage
        
        self.installer.intf.setHelpline(_("F1-Help  F2-New  F3-Edit  F4-Delete  F5-Reset  F12-OK"))
        
        self.g = GridForm(self.screen, _("Partitioning"), 1, 5)
        self.lb = CListbox(height=10, cols=4,
                           col_widths=[22,14,14,10],
                           scroll=1, returnExit = 1,
                           width=70, col_pad=2,
                           col_labels=[_('Device'), _('Mount Point'), _("Filesystem"), _('Size') ],
                           col_label_align=[LEFT, LEFT, LEFT, CENTER])
        self.g.add(self.lb, 0, 1)
        
        self.bb = ButtonBar(self.screen, ((_("New"), "new", "F2"),
                                          (_("Edit"), "edit", "F3"),
                                          (_("Delete"), "delete", "F4"),
                                          TEXT_OK_BUTTON, TEXT_BACK_BUTTON))

        self.g.add(self.bb, 0, 2, (0, 1, 0, 0))
        self.g.addHotKey("F5")

        while 1:
            self.populate()
            rc = self.g.run()
            button = self.bb.buttonPressed(rc)
            
            if button == "new":
                self.newCb()
            elif button == "edit" or rc == self.lb.listbox: # XXX better way?
                self.editCb()
            elif button == "delete":
                self.deleteCb()
            elif button == "reset" or rc == "F5":
                self.storage.reset()
            elif button == TEXT_BACK_CHECK:
                self.storage.reset()

                self.screen.popHelpLine()
                self.screen.popWindow()
                return INSTALL_BACK
            else:
                #if not self.partitions.getRequestByMountPoint("/"):
                #    self.intf.messageWindow(_("No Root Partition"),
                #        _("Installation requires a / partition."))
                #    continue

                #(errors, warnings) = self.partitions.sanityCheckAllRequests(self.diskset)
                #rc = partitionSanityErrors(self.intf, errors)
                #if rc != 1:
                #    continue

                #rc = partitionSanityWarnings(self.intf, warnings)
                #if rc != 1:
                #    continue

                #warnings = getPreExistFormatWarnings(self.partitions,
                #                                     self.diskset)
                #rc = partitionPreExistFormatWarnings(self.intf, warnings)
                #if rc != 1:
                #    continue

                self.screen.popHelpLine()
                self.screen.popWindow()
                return INSTALL_OK
        
        return INSTALL_OK
