#!/bin/bash
# Adapter-only environment. Never force SDL video/audio drivers here.
BIN="$GAMEDIR/bin/aarch64/magicrampage-nextos"
export BIN
# Bundled libs so the port is self-contained on CFWs that do not ship them.
# libzip.so.5 (+ libbz2.so.1.0, liblzma.so.5) is present on muOS/Knulli but NOT
# on plain ArkOS, where the loader used to die with
# "libzip.so.5: cannot open shared object" (status 127). Prepending the bundled
# dir keeps every other lib coming from the firmware/PortMaster as before.
if [ -d "$GAMEDIR/lib/aarch64" ]; then
  export LD_LIBRARY_PATH="$GAMEDIR/lib/aarch64${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi
MAGICRAMPAGE_SDL_PROVIDER=/usr/lib/aarch64-linux-gnu/libmali-bifrost-g31-rxp0-gbm.so
if [ -f "$MAGICRAMPAGE_SDL_PROVIDER" ] && [ ! -L "$MAGICRAMPAGE_SDL_PROVIDER" ]; then
  export MAGICRAMPAGE_SDL_PROVIDER
else
  unset MAGICRAMPAGE_SDL_PROVIDER
fi
printf '[adapter] magicrampage aarch64; inherited video/audio; bundled libzip; PortMaster controller mapping\n'
