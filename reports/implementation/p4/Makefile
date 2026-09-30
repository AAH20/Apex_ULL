# Makefile for P4 Implementation
# Build: make all
# Test:  make test
# Clean: make clean

P4C = p4c
TARGET = bmv2
ARCH = v1model

TARGETS = simple_forwarder.json simple_forwarder.p4info.txt

.PHONY: all test clean

all: $(TARGETS)

simple_forwarder.json: simple_forwarder.p4
	$(P4C) --target $(TARGET) --arch $(ARCH) -o $@ $<

simple_forwarder.p4info.txt: simple_forwarder.p4
	$(P4C) --target $(TARGET) --arch $(ARCH) --p4info-out $@ $<

test: all
	python3 test_p4.py --compile

clean:
	rm -f $(TARGETS) *.log
