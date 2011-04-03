
NAME = network
VER  = 0.99.0

DESTDIR=

all:
	@echo "Nothing to do here."

install:
	-mkdir -pv $(DESTDIR)/etc/{network,ppp}
	-mkdir -pv $(DESTDIR)/lib/network
	-mkdir -pv $(DESTDIR)/sbin
	-mkdir -pv $(DESTDIR)/var/log/network

	install -m 755 -v network $(DESTDIR)/sbin

	cp -rfv {hooks,header*,functions*} $(DESTDIR)/lib/network/

	install -m 755 -v ppp/ip-updown $(DESTDIR)/etc/ppp
	ln -svf ip-updown $(DESTDIR)/etc/ppp/ip-pre-up
	ln -svf ip-updown $(DESTDIR)/etc/ppp/ip-up
	ln -svf ip-updown $(DESTDIR)/etc/ppp/ip-down
	install -m 755 -v ppp/dialer $(DESTDIR)/etc/ppp

dist:
	git archive --format tar --prefix $(NAME)-$(VER)/ HEAD | gzip -9 > \
		$(NAME)-$(VER).tar.gz
