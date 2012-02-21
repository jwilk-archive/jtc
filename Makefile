.PHONY: all
all: check

.PHONY: check
check:
	nosetests -v

.PHONY: clean
clean:
	$(RM) *.pyc parser.out parsetab.*

# vim:ts=4
