{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/release-21.11";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachSystem
      (with flake-utils.lib.system; [ x86_64-linux i686-linux ])
      (system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          myPythonPackages =
            (packages: with packages; [
              evdev
            ]);

          qkmDerivation = ({ pythonEnv, ... }:
            pkgs.stdenv.mkDerivation {
              name = "qkm";
              buildInputs = [
                pythonEnv
              ];
              unpackPhase = "true";
              installPhase = ''
                mkdir -p $out/bin
                cp ${./main.py} $out/bin/qkm
                chmod +x $out/bin/qkm
              '';
            });
        in
        rec {
          packages = {
            pythonEnv = pkgs.python3.withPackages myPythonPackages;
            qkm = qkmDerivation { pythonEnv = packages.pythonEnv; };
          };
          defaultPackage = packages.qkm;
          devShell = packages.pythonEnv.env;
        });
}
