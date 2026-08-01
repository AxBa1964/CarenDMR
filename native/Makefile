CC ?= clang
CFLAGS ?= -O2
CFLAGS += -std=c11 -fPIC -fvisibility=hidden -Wall -Wextra -Werror

ifeq ($(shell uname -s),Darwin)
NM_GLOBAL = nm -gU
else
CFLAGS += -D_DEFAULT_SOURCE
NM_GLOBAL = nm -g --defined-only
endif

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
	@test "$$($(NM_GLOBAL) $(LIBRARY) | awk '{print $$3}' | wc -l | tr -d ' ')" = "3"
	$(NM_GLOBAL) $(LIBRARY) | grep carendmr_mbe_decode
	@if $(NM_GLOBAL) $(LIBRARY) | grep -Eq '(^|_)mbe.*[Ee]ncode'; then \
		echo "unexpected encoder symbol in receive-only library"; \
		exit 1; \
	fi

clean:
	rm -f libcarendmr_mbe.dylib libcarendmr_mbe.so
