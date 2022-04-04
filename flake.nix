{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        myPythonPackages = (packages: with packages; [
          evdev
        ]);
      in
      rec {
        packages = {
          pythonEnv = pkgs.python3.withPackages myPythonPackages;
        };
        devShell = packages.pythonEnv.env;
      });
}
