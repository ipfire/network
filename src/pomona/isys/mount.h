
#ifndef H_MOUNT
#define H_MOUNT

#define MOUNT_ERR_ERRNO	1
#define MOUNT_ERR_OTHER	2

#include <sys/mount.h>		/* for umount() */

int doPwMount(char *dev, char *where, char *fs, char *options, char **err);
int mkdirChain(char * origChain);

#endif
