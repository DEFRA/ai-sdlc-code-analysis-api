{ pkgs ? import <nixpkgs> { } }:

let
  openssl = pkgs.openssl.dev;
  sqlite = pkgs.sqlite.dev;
  tcl = pkgs.tcl;
  tk = pkgs.tk;
in pkgs.mkShell {
  buildInputs = [
    openssl
    pkgs.gnumake
    pkgs.zlib
    pkgs.readline
    pkgs.libffi
    pkgs.xz
    pkgs.ncurses
    pkgs.pkg-config
    pkgs.stdenv.cc.cc.lib
    sqlite
    tcl
    tk
  ];

  shellHook = ''
    export PYENV_ROOT="$HOME/.pyenv"
    export PATH="$PYENV_ROOT/bin:$PATH"
    eval "$(pyenv init -)"

    export CPPFLAGS="-I${openssl}/include -I${sqlite}/include -I${tk}/include"
    export LDFLAGS="-L${openssl}/lib -L${sqlite}/lib -L${tk}/lib"
    export PKG_CONFIG_PATH="${openssl}/lib/pkgconfig:${sqlite}/lib/pkgconfig:${tk}/lib/pkgconfig"
    export LD_LIBRARY_PATH="${pkgs.stdenv.cc.cc.lib}/lib:$LD_LIBRARY_PATH"
  '';
}
