.PHONY: all clean sanity-x sanity-py

all: sanity-py sanity-x

sanity-x:
	./Make-sanity -X

sanity-py:
	./Make-sanity -P

clean:
	$(RM) *.pyc parser.out parsetab.*

# vim:ts=4
