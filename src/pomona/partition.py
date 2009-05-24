#!/usr/bin/python

from snack import *

from storage.deviceaction import *
import storage
import storage.formats as formats
from storage.devicelibs.lvm import safeLvmName

from constants import *

import gettext
_ = lambda x: gettext.ldgettext("pomona", x)

def logicalVolumeGroupList(installer):
    storage = installer.ds.storage
    
    vgs = []
    for vg in storage.vgs:
        vgs.append(vg.name)
    (button, choice) = ListboxChoiceWindow(installer.intf.screen,
                           _("Volume Group Selection"),
                           _("What language would you like to use during the "
                             "installation process?"), vgs,
                           buttons = [TEXT_OK_BUTTON, TEXT_BACK_BUTTON],
                           width = 30, scroll = 1,
                           height = min((8, len(vgs))))
    if button == TEXT_BACK_CHECK:
        return
    
    for vg in storage.vgs:
        if choice == vg.name:
            return vg
    return

class PartitionWindow(object):
    def populate(self):
        self.lb.clear()

        for vg in self.storage.vgs:
            self.lb.append([vg.name, "", "", "",], vg)
            
            freespace = vg.freeSpace
            if freespace:
                self.lb.append(["  %s" % _("Free Space"), "", "", "%dM" % freespace,],
                               None, [LEFT, LEFT, LEFT, RIGHT])
            
        for disk in self.storage.disks:
            self.lb.append([disk.path, "", "", "",], None)
            for part in self.storage.partitions:
                if disk == part.disk:
                    mountpoint = type = ""
                    if part.format:
                        type = part.format.name
                        try:
                            if part.format.mountpoint:
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
    
    def makeVGName(self, device):
        grid = Grid(2, 1)
        label = Label(_("VG Name:"))
        grid.setField(label, 0, 0, (0,0,0,0), anchorLeft = 1)
        name = Entry(20, device.name)
        grid.setField(name, 1, 0, anchorRight = 1, growx = 1)
        return (grid, name)

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
            self.newPart()
        elif choice == _("RAID"):
            pass # XXX self.newRaid()
        elif choice == _("Logical Volume Group"):
            self.newVG()
        elif choice == _("Logical Volume Device"):
            self.newLV()

    def newPart(self):
        disks = []
        for disk in self.storage.disks:
            disks.append(("%s - %s" % (disk.name, disk.model,), disk,))

        (button, disk) = ListboxChoiceWindow(self.installer.intf.screen,
                                             _("Disk Selection"),
                                             _("Choose the disk you want create the new "
                                               "partition on."),
                                             disks, buttons = [TEXT_OK_BUTTON, TEXT_CANCEL_BUTTON],
                                             height=len(disks))
        if button == TEXT_CANCEL_CHECK:
            return

        device = self.storage.newPartition(parents=disk)
        self.editPart(device=device)

    def newVG(self):
        device = self.storage.newVG()
        self.storage.createDevice(device)
        self.editVG(device=device)
    
    def newLV(self):
        vg = logicalVolumeGroupList(self.installer)
        if vg:
            device = self.storage.newLV(vg=vg)
        self.editLV(device=device)

    def editPart(self, device):
        if not device:
            return
        
        row = 0
        actions = []
        
        if not device.exists:
            tstr = _("Add Partition")
        else:
            tstr = _("Edit Partition")
        grid = GridForm(self.screen, tstr, 1, 6)
        
        if device.exists:
            if device.format.exists and getattr(device.format, "label", None):
                lbl = Label("%s %s" % (_("Original File System Label:"), device.format.label))
                grid.add(lbl, 0, row)
                row += 1
        
        (mountgrid, mountpoint) = self.makeMountPoint(device)
        grid.add(mountgrid, 0, row)
        row += 1
        
        if not device.exists:
            subgrid1 = Grid(2, 1)
            
            (fsgrid, fstype) = self.makeFileSystemList(device)
            subgrid1.setField(fsgrid, 0, 0)

            #(devgrid, drivelist) = self.makeDriveList(device)
            #subgrid1.setField(devgrid, 0, 0)
            
            #(fsgrid, fstype) = self.makeFileSystemList(device)
            #subgrid1.setField(fsgrid, 1, 0, (1,0,0,0), growx=1)
            
            grid.add(subgrid1, 0, row, (0,1,0,0), growx=1)
            row += 1
        else:
            pass
        
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
                
            if not device.exists:
                actions.append(ActionCreateDevice(self.installer, device))

            break
        
        self.screen.popWindow()
        return actions

    def editVG(self, device):
        if not device.exists:
            tstr = _("Add Logical Volume Group")
        else:
            tstr = _("Edit Logical Volume Group")
        grid = GridForm(self.screen, tstr, 1, 6)
        row = 0
        
        (namegrid, name) = self.makeVGName(device)
        grid.add(namegrid, 0, row)
        row += 1
        
        # XXX size?
        
        bb = ButtonBar(self.screen, (TEXT_OK_BUTTON, TEXT_CANCEL_BUTTON))
        grid.add(bb, 0, row, (0,1,0,0), growx = 1)
        row += 1
        
        while 1:
            rc = grid.run()
            button = bb.buttonPressed(rc)

            if button == TEXT_CANCEL_CHECK:
                break

            if not name.value():
                self.installer.intf.messageWindow(_("Error"),
                                                  _("You must enter a name for the "
                                                    "Logical Volume Group."))
                continue
            device.name = safeLvmName(name.value())

            break

        self.screen.popWindow()
        
    editLV = editPart
        
    def editCb(self):
        device = self.lb.current()
        if not device:
            self.installer.intf.messageWindow(_("Unable To Edit"),
                                              _("You must first select a partition to edit."))
            return
        
        reason = self.storage.deviceImmutable(device)
        if reason:
            self.installer.intf.messageWindow(_("Unable To Edit"),
                                              _("You cannot edit this device:\n\n%s")
                                              % reason,)
            return

        actions = None
        if device.type == "mdarray":
            pass #self.editRaidArray(device)
        elif device.type == "lvmvg":
            actions = self.editVG(device)
        elif device.type == "lvmlv":
            actions = self.editLV(device)
        elif isinstance(device, storage.devices.PartitionDevice):
            actions = self.editPart(device)
        
        for action in actions:
            self.storage.devicetree.registerAction(action)

    def deleteCb(self):
        device = self.lb.current()

        if not device:
            self.installer.intf.messageWindow(_("Unable To Delete"),
                                              _("You must first select a partition to delete."))
            return
        
        if device.type == "lvmvg":
            text = _("Do you really want to delete the selected Logical Volume Group and "
                     "all its Logical Volumes?")
        else:
            text = _("Do you really want to delete the selected partition?")

        if not self.installer.intf.messageWindow(_("Confirm Delete"), text, type="yesno"):
            return
        
        self.storage.destroyDevice(device)

    def __call__(self, installer):
        self.installer = installer
        self.screen = self.installer.intf.screen
        self.storage = self.installer.ds.storage
        
        self.installer.intf.setHelpline(_("F2-New  F3-Edit  F4-Delete  F5-Reset  F12-OK"))
        
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
