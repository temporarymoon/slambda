{
  description = "Slambda: a scuffed chording script for linux.";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/release-21.11";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachSystem
      (with flake-utils.lib.system; [ x86_64-linux aarch64-linux ])
      (system:
        let
          pkgs = nixpkgs.legacyPackages.${system};

          slambda = pkgs.writers.writePython3Bin "slambda"
            {
              libraries = [ pkgs.python3Packages.evdev ];
              flakeIgnore = [
                "E261" # Requires 2 spaces between code and comments
              ];
            }
            ./main.py;
        in
        rec {
          packages = {
            inherit slambda;
          };

          overlays.default = final: prev: {
            slambda = self.packages.${prev.system}.default;
          };

          nixosModules.default = { ... }: {
            imports = [
              ./nixos-module.nix
              { nixpkgs.overlays = [ self.overlays.default ]; }
            ];
          };

          defaultPackage = packages.slambda;
        });
}
