#
# partIntfHelpers.py: partitioning interface helper functions
#
# Matt Wilson <msw@redhat.com>
# Jeremy Katz <katzj@redhat.com>
# Mike Fulbright <msf@redhat.com>
# Harald Hoyer <harald@redhat.de>
#
# Copyright 2002 Red Hat, Inc.
#
# This software may be freely redistributed under the terms of the GNU
# library public license.
#
# You should have received a copy of the GNU Library Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#
"""Helper functions shared between partitioning interfaces."""

import string

from constants import *
import partedUtils
import parted
import fsset
import partRequests
from pyfire.translate import _

def sanityCheckMountPoint(mntpt, fstype, preexisting, format):
	"""Sanity check that the mountpoint is valid.
	
	mntpt is the mountpoint being used.
	fstype is the file system being used on the request.
	preexisting is whether the request was preexisting (request.preexist)
	format is whether the request is being formatted or not
	"""
	if mntpt:
		passed = 1
		if not mntpt:
			passed = 0
		else:
			if mntpt[0] != '/' or (len(mntpt) > 1 and mntpt[-1:] == '/'):
				passed = 0
			elif mntpt.find(' ') > -1:
				passed = 0
                
		if not passed:
			return _("The mount point %s is invalid.  Mount points must start "
							 "with '/' and cannot end with '/', and must contain "
							 "printable characters and no spaces." % mntpt)
		else:
			return None
	else:
		if (fstype and fstype.isMountable() and (not preexisting or format)):
			return _("Please specify a mount point for this partition.")
		else:
			# its an existing partition so don't force a mount point
			return None

def isNotChangable(request, requestlist):
	return None

def doDeletePartitionByRequest(intf, requestlist, partition, confirm=1, quiet=0):
	"""Delete a partition from the request list.
	
	intf is the interface
	requestlist is the list of requests
	partition is either the part object or the uniqueID if not a part
	"""

	if partition == None:
		intf.messageWindow(_("Unable To Delete"),
											 _("You must first select a partition to delete."),
											custom_icon="error")
		return 0

	if partition.type & parted.PARTITION_FREESPACE:
		intf.messageWindow(_("Unable To Delete"),
											 _("You cannot delete free space."),
											custom_icon="error")
		return 0
	else:
		device = partedUtils.get_partition_name(partition)

	ret = requestlist.containsImmutablePart(partition)
	if ret:
		if not quiet:
			intf.messageWindow(_("Unable To Delete"),
												 _("You cannot delete this "
													 "partition, as it is an extended partition "
													 "which contains %s")
													% (ret), custom_icon="error")
		return 0

	# see if device is in our partition requests, remove
	request = requestlist.getRequestByDeviceName(device)
	
	if request:
		state = isNotChangable(request, requestlist)
		
		# If the partition is protected, we also can't delete it so specify a
		# reason why.
		if state is None and request.getProtected():
			state = _("This partition is holding the data for the hard "
								"drive install.")

		if state:
			if not quiet:
				intf.messageWindow(_("Unable To Delete"),
													 _("You cannot delete this partition:\n\n") + state,
													custom_icon="error")
			return (None, None)

		if confirm and not confirmDeleteRequest(intf, request):
			return 0

		if request.getPreExisting():
			if isinstance(request, partRequests.PartitionSpec):
				# get the drive
				drive = partedUtils.get_partition_drive(partition)

				if partition.type & parted.PARTITION_EXTENDED:
					requestlist.deleteAllLogicalPartitions(partition)

				delete = partRequests.DeleteSpec(drive, partition.geom.start, partition.geom.end)
				requestlist.addDelete(delete)
				
		# now remove the request
		requestlist.removeRequest(request)
	else: # is this a extended partition we made?
		if partition.type & parted.PARTITION_EXTENDED:
			requestlist.deleteAllLogicalPartitions(partition)
		else:
			#raise ValueError, "Deleting a non-existent partition"
			return 0

	del partition
	return 1

def doDeletePartitionsByDevice(intf, requestlist, diskset, device,
			confirm=1, quiet=0):
	""" Remove all partitions currently on device """
	if confirm:
		rc = intf.messageWindow(_("Confirm Delete"),
														_("You are about to delete all partitions on "
															"the device '/dev/%s'.") % (device,),
														type="custom", custom_icon="warning",
														custom_buttons=[_("Cancel"), _("_Delete")])
		if not rc:
			return

		requests = requestlist.getRequestsByDevice(diskset, device)
		if not requests:
			return

	# get list of unique IDs of these requests
	reqIDs = []
	for req in requests:
		part = partedUtils.get_partition_by_name(diskset.disks, req.device)
		if part.type & parted.PARTITION_FREESPACE or part.type & parted.PARTITION_METADATA or part.type & parted.PARTITION_PROTECTED:
			continue
		reqIDs.append(req.uniqueID)

	# now go thru and try to delete the unique IDs
	for id in reqIDs:
		try:
			req = requestlist.getRequestByID(id)
			if req is None:
				continue
			part = partedUtils.get_partition_by_name(diskset.disks, req.device)
			rc = doDeletePartitionByRequest(intf, requestlist, part, confirm=0, quiet=1)
			# not sure why it returns both '0' and '(None, None)' on failure
			if not rc or rc == (None, None):
				pass
		except:
			pass

	# see which partitions are left
	notdeleted = []
	left_requests = requestlist.getRequestsByDevice(diskset, device)
	if left_requests:
		# get list of unique IDs of these requests
		leftIDs = []
		for req in left_requests:
			part = partedUtils.get_partition_by_name(diskset.disks, req.device)
			if part.type & parted.PARTITION_FREESPACE or part.type & parted.PARTITION_METADATA or part.type & parted.PARTITION_PROTECTED:
				continue
			leftIDs.append(req.uniqueID)

	for id in leftIDs:
		req = requestlist.getRequestByID(id)
		notdeleted.append(req)
	    

	# see if we need to report any failures - some were because we removed
	# an extended partition which contained other members of our delete list
	outlist = ""
	for req in notdeleted:
		newreq = requestlist.getRequestByID(req.uniqueID)
		if newreq:
			outlist = outlist + "\t/dev/%s\n" % (newreq.device,)

			if outlist != "" and not quiet:
				intf.messageWindow(_("Notice"),
													 _("The following partitions were not deleted "
														 "because they are in use:\n\n%s") % outlist,
													custom_icon="warning")

	return 1

def doEditPartitionByRequest(intf, requestlist, part):
	"""Edit a partition from the request list.
	
	intf is the interface
	requestlist is the list of requests
	partition is either the part object or the uniqueID if not a part
	"""
    
	if part == None:
		intf.messageWindow(_("Unable To Edit"),
											 _("You must select a partition to edit"), custom_icon="error")
		return (None, None)

	if part.type & parted.PARTITION_FREESPACE:
		request = partRequests.PartitionSpec(fsset.fileSystemTypeGetDefault(),
							start = partedUtils.start_sector_to_cyl(part.geom.dev, part.geom.start),
							end = partedUtils.end_sector_to_cyl(part.geom.dev, part.geom.end),
							drive = [ partedUtils.get_partition_drive(part) ])

		return ("NEW", request)
	elif part.type & parted.PARTITION_EXTENDED:
		return (None, None)
    
	ret = requestlist.containsImmutablePart(part)
	if ret:
		intf.messageWindow(_("Unable To Edit"),
											 _("You cannot edit this "
												 "partition, as it is an extended partition "
												 "which contains %s") %(ret), custom_icon="error")
		return 0

	name = partedUtils.get_partition_name(part)
	request = requestlist.getRequestByDeviceName(name)
	if request:
		state = isNotChangable(request, requestlist)
		if state is not None:
			intf.messageWindow(_("Unable To Edit"),
												 _("You cannot edit this partition:\n\n") + state,
												 custom_icon="error")
			return (None, None)
	
		return ("PARTITION", request)
	else: # shouldn't ever happen
		raise ValueError, ("Trying to edit non-existent partition %s"
			% (partedUtils.get_partition_name(part)))


def checkForSwapNoMatch(pomona):
	"""Check for any partitions of type 0x82 which don't have a swap fs."""
	for request in pomona.id.partitions.requests:
		if not request.device or not request.fstype:
			continue
		
		part = partedUtils.get_partition_by_name(pomona.id.diskset.disks, request.device)
		
		if (part and (not part.type & parted.PARTITION_FREESPACE)
						 and (part.native_type == 0x82)
						 and (request.fstype and request.fstype.getName() != "swap")
						 and (not request.format)):
			rc = pomona.intf.messageWindow(_("Format as Swap?"),
																		 _("/dev/%s has a partition type of 0x82 "
																			 "(Linux swap) but does not appear to "
																			 "be formatted as a Linux swap "
																			 "partition.\n\n"
																			 "Would you like to format this "
																			 "partition as a swap partition?")
																		% (request.device), type = "yesno",
																			custom_icon="question")
			if rc == 1:
				request.format = 1
				request.fstype = fsset.fileSystemTypeGet("swap")
				partedUtils.set_partition_file_system_type(part, request.fstype)
				

def mustHaveSelectedDrive(intf):
	txt =_("You need to select at least one hard drive to install %s.") % (name,)
	intf.messageWindow(_("Error"), txt, custom_icon="error")
     
def queryNoFormatPreExisting(intf):
	"""Ensure the user wants to use a partition without formatting."""
	txt = _("You have chosen to use a pre-existing "
					"partition for this installation without formatting it. "
					"We recommend that you format this partition "
					"to make sure files from a previous operating system installation "
					"do not cause problems with this installation of Linux. "
					"However, if this partition contains files that you need "
					"to keep, such as home directories, then  "
					"continue without formatting this partition.")
	rc = intf.messageWindow(_("Format?"), txt, type = "custom",
		custom_buttons=[_("_Modify Partition"), _("Do _Not Format")],
		custom_icon="warning")
	return rc

def partitionSanityErrors(intf, errors):
	"""Errors were found sanity checking.  Tell the user they must fix."""
	rc = 1
	if errors:
		errorstr = string.join(errors, "\n\n")
		rc = intf.messageWindow(_("Error with Partitioning"),
														_("The following critical errors exist "
															"with your requested partitioning "
															"scheme. "
															"These errors must be corrected prior "
															"to continuing with your install of "
															"%s.\n\n%s") %(name, errorstr),
														custom_icon="error")
	return rc

def partitionSanityWarnings(intf, warnings):
	"""Sanity check found warnings.  Make sure the user wants to continue."""
	rc = 1
	if warnings:
		warningstr = string.join(warnings, "\n\n")
		rc = intf.messageWindow(_("Partitioning Warning"),
														_("The following warnings exist with "
															"your requested partition scheme.\n\n%s"
															"\n\nWould you like to continue with "
															"your requested partitioning "
															"scheme?") % (warningstr),
														type="yesno", custom_icon="warning")
	return rc


def partitionPreExistFormatWarnings(intf, warnings):
	"""Double check that preexistings being formatted are fine."""
	rc = 1
	if warnings:
		labelstr1 = _("The following pre-existing partitions have been "
									"selected to be formatted, destroying all data.")
		labelstr2 = _("Select 'Yes' to continue and format these "
									"partitions, or 'No' to go back and change these "
									"settings.")
		commentstr = ""
		for (dev, type, mntpt) in warnings:
			commentstr = commentstr + "/dev/%s %s %s\n" % (dev,type,mntpt)
		rc = intf.messageWindow(_("Format Warning"), "%s\n\n%s\n\n%s" %
														(labelstr1, labelstr2, commentstr),
														type="yesno", custom_icon="warning")
	return rc

def getPreExistFormatWarnings(partitions, diskset):
	"""Return a list of preexisting partitions being formatted."""

	devs = []
	for request in partitions.requests:
		if request.getPreExisting() == 1:
			devs.append(request.uniqueID)

	devs.sort()
    
	rc = []
	for dev in devs:
		request = partitions.getRequestByID("%s" % (dev,))
		if request.format:
			if request.fstype.isMountable():
				mntpt = request.mountpoint
			else:
				mntpt = ""

			if isinstance(request, partRequests.PartitionSpec):
				dev = request.device
			rc.append((dev, request.fstype.getName(), mntpt))

	if len(rc) == 0:
		return None
	else:
		return rc
            
def confirmDeleteRequest(intf, request):
	"""Confirm the deletion of a request."""
	if not request:
		return
    
	if request.device:
		errmsg = _("You are about to delete the /dev/%s partition.") % (request.device,)
	else:
		errmsg = _("The partition you selected will be deleted.")

	rc = intf.messageWindow(_("Confirm Delete"), errmsg, type="custom",
		custom_buttons=[_("Cancel"), _("_Delete")], custom_icon="question")

	return rc

def confirmResetPartitionState(intf):
	"""Confirm reset of partitioning to that present on the system."""
	rc = intf.messageWindow(_("Confirm Reset"),
													_("Are you sure you want to reset the "
														"partition table to its original state?"),
													type="yesno", custom_icon="question")
	return rc
