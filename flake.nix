{
  description = "Slambda: a scuffed chording script for linux.";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/release-21.11";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    let
      # List of supported systems:
      supportedSystems = [
        "x86_64-linux"
        "aarch64-linux"
      ];

      forAllSystems = f:
        nixpkgs.lib.genAttrs supportedSystems (system: f system);
    in
    rec {
      packages = forAllSystems (system:
        let pkgs = nixpkgs.legacyPackages.${system};
        in
        {
          slambda = pkgs.writers.writePython3Bin "slambda"
            {
              libraries = [ pkgs.python3Packages.evdev ];
              flakeIgnore = [
                "E261" # Requires 2 spaces between code and comments
              ];
            }
            ./main.py;
        });

      defaultPackage = forAllSystems
        (system: packages.${system}.slambda);

      overlays.default = final: prev: {
        slambda = self.packages.${prev.system}.slambda;
      };

      nixosModule = { ... }: {
        imports = [
          ./nixos-module.nix
          { nixpkgs.overlays = [ self.overlays.default ]; }
        ];
      };
    };
}
