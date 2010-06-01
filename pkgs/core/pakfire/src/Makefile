
SUBSTITUDE = sed -e "s/@VERSION@/$(VERSION)/g"

PYTHON_MAJ = "2.6"
PYTHON_DIR = $(DESTDIR)/usr/lib/python$(PYTHON_MAJ)/site-packages/pakfire

all: pakfire

pakfire: pakfire.in
	#$(SUBSTITUDE) pakfire.in > pakfire

	# XXX Just for now:
	cp -vf pakfire.sh pakfire

clean:
	rm -vf pakfire python/*.py[co]

install: pakfire
	-mkdir -pv $(DESTDIR)/usr/bin
	install -v -m 755 pakfire $(DESTDIR)/usr/bin
	-mkdir -pv $(PYTHON_DIR)
	cp -vf python/*.py $(PYTHON_DIR)/
	-mkdir -pv $(DESTDIR)/etc/pakfire.repos.d $(DESTDIR)/var/cache/pakfire
