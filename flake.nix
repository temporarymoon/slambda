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
          qkm = pkgs.writers.writePython3Bin "qkm"
            {
              libraries = [ pkgs.python3Packages.evdev ];
              flakeIgnore = [ "E261" ];
            }
            ./main.py;
        in
        rec {
          packages = {
            inherit qkm;
          };
          defaultPackage = packages.qkm;
        });
}
