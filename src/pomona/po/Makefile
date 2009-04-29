
include ../Makefile.inc

POTFILES = ../*.py
NONPOTFILES = ../lang-table

POS = $(wildcard *.po)
FMTCATALOGS = $(patsubst %.po,%.mo,$(POS))

MSGMERGE = msgmerge -v

all: $(FMTCATALOGS) report

$(PSNAME).pot: $(POTFILES) $(NONPOTFILES)
	xgettext --from-code=UTF-8 --default-domain=pomona \
		--keyword=_ --keyword=N_ $(POTFILES)
	cat ../lang-table | cut -f1 | while read line; do echo -e "\n#. generated from lang-table\nmsgid \"$$line\"\nmsgstr \"\""; done >> pomona.po
	if cmp -s pomona.po pomona.pot; then \
	    rm -f pomona.po; \
	else \
	    mv pomona.po pomona.pot; \
	fi

refresh-po:
	for cat in $(POS); do \
		lang=`basename $$cat .po`; \
		if $(MSGMERGE) $$lang.po pomona.pot > $$lang.pot ; then \
			mv -f $$lang.pot $$lang.po ; \
			echo "$(MSGMERGE) of $$lang succeeded" ; \
		else \
			echo "$(MSGMERGE) of $$lang failed" ; \
			rm -f $$lang.pot ; \
		fi \
	done

update-po: $(PSNAME).pot refresh-po

install: all
	mkdir -p $(INSTALLNLSDIR)
	for n in $(FMTCATALOGS); do \
	    l=`basename $$n .mo`; \
	    $(INSTALL) -m 755 -d $(INSTALLNLSDIR)/$$l; \
	    $(INSTALL) -m 755 -d $(INSTALLNLSDIR)/$$l/LC_MESSAGES; \
	    $(INSTALL) -m 644 $$n \
				$(INSTALLNLSDIR)/$$l/LC_MESSAGES/pomona.mo; \
	done

%.mo: %.po
	msgfmt --check -o $@ $<

report:
	@for cat in $(POS); do \
		echo -n "$$cat: "; \
		msgfmt -v --statistics -o /dev/null $$cat; \
	done

clean:
	rm -f *.mo missing
