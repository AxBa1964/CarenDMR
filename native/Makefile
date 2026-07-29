CC ?= clang
CFLAGS ?= -O2
CFLAGS += -std=c11 -fPIC -fvisibility=hidden -Wall -Wextra -Werror

SOURCES = \
	carendmr_mbe.c \
	mbelib/ambe3600x2450.c \
	mbelib/ecc.c \
	mbelib/mbelib.c

ifeq ($(shell uname -s),Darwin)
LIBRARY = libcarendmr_mbe.dylib
SHARED_FLAGS = -dynamiclib
else
LIBRARY = libcarendmr_mbe.so
SHARED_FLAGS = -shared
endif

.PHONY: all clean check

all: $(LIBRARY)

$(LIBRARY): $(SOURCES) carendmr_mbe.h
	$(CC) $(CFLAGS) $(SHARED_FLAGS) -I. -Imbelib $(SOURCES) -lm -o $@

check: $(LIBRARY)
	@test "$$(nm -gU $(LIBRARY) | awk '{print $$3}' | wc -l | tr -d ' ')" = "3"
	nm -gU $(LIBRARY) | grep carendmr_mbe_decode
	@if nm -gU $(LIBRARY) | grep -Eq '(^|_)mbe.*[Ee]ncode'; then \
		echo "unexpected encoder symbol in receive-only library"; \
		exit 1; \
	fi

clean:
	rm -f libcarendmr_mbe.dylib libcarendmr_mbe.so
