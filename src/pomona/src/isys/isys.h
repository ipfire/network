#ifndef H_ISYS
#define H_ISYS

#define MIN_RAM						32000
#define EARLY_SWAP_RAM		64000


int insmod(char * modName, char * path, char ** args);
int rmmod(char * modName);

/* returns 0 for true, !0 for false */
int fileIsIso(const char * file);

/* returns 1 if on an iSeries vio console, 0 otherwise */
int isVioConsole(void);

#endif
