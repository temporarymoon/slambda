# Slightly modified version of [this](https://github.com/kmonad/kmonad/blob/master/nix/nixos-module.nix)
{ config, lib, pkgs, ... }:

let
  cfg = config.services.slambda;

  # Per-keyboard options:
  keyboard = { name, ... }: {
    options = {
      name = lib.mkOption {
        type = lib.types.str;
        example = "laptop-internal";
        description = "Keyboard name.";
      };

      device = lib.mkOption {
        type = lib.types.path;
        example = "/dev/input/by-id/some-dev";
        description = "Path to the keyboard's device file.";
      };

      extraGroups = lib.mkOption {
        type = lib.types.listOf lib.types.str;
        default = [ ];
        example = [ "openrazer" ];
        description = ''
          Extra permission groups to attach to the Slambda instance for
          this keyboard.
          Since Slambda runs as an unprivileged user, it may sometimes
          need extra permissions in order to read the keyboard device
          file.  If your keyboard's device file isn't in the input
          group you'll need to list its group in this option.
        '';
      };

      delay = lib.mkOption {
        type = lib.types.int;
        description = "The delay (in milliseconds) used to detect chords.";
      };

      chords = lib.mkOption {
        type = with lib.types; listOf (submodule {
          options = {
            from = lib.mkOption { type = listOf str; };
            to = lib.mkOption { type = listOf str; };
          };
        });

        example = [{ from = [ "a" "b" ]; to = [ "c" "d" ]; }];

        description = "Define chords to process for this keyboard";
      };
    };

    config = {
      name = lib.mkDefault name;
    };
  };

  # Create a complete Slambda configuration file:
  mkConfig = keyboard:
    let
      config = {
        device = keyboard.device;
        name = keyboard.name;
        delay = keyboard.delay;
        chords = keyboard.chords;
        log = true;
      };
    in
    pkgs.writeTextFile {
      name = "slambda-${keyboard.name}.json";
      text = builtins.toJSON config;
    };

  # Build a systemd path config that starts the service below when a
  # keyboard device appears:
  mkPath = keyboard: rec {
    name = "slambda-${keyboard.name}";
    value = {
      description = "Slambda trigger for ${keyboard.device}";
      wantedBy = [ "default.target" ];
      pathConfig.Unit = "${name}.service";
      pathConfig.PathExists = keyboard.device;
    };
  };

  # Build a systemd service that starts Slambda:
  mkService = keyboard:
    let
      cmd = [
        "${cfg.package}/bin/slambda"
      ] ++ cfg.extraArgs ++ [
        "${mkConfig keyboard}"
      ];

      groups = [
        "input"
        "uinput"
      ] ++ keyboard.extraGroups;
    in
    {
      name = "slambda-${keyboard.name}";
      value = {
        description = "Slambda for ${keyboard.device}";
        script = lib.escapeShellArgs cmd;
        serviceConfig.Restart = "no";
        serviceConfig.User = "slambda";
        serviceConfig.SupplementaryGroups = groups;
        serviceConfig.Nice = -20; # Highest cpu priority!
      };
    };
in
{
  options.services.slambda = {
    enable = lib.mkEnableOption "Slambda: a scuffed chording script";

    package = lib.mkOption {
      type = lib.types.package;
      default = pkgs.slambda;
      description = "The Slambda package to use.";
    };

    keyboards = lib.mkOption {
      type = lib.types.attrsOf (lib.types.submodule keyboard);
      default = { };
      description = "Keyboard configuration.";
    };

    extraArgs = lib.mkOption {
      type = lib.types.listOf lib.types.str;
      default = [ ];
      description = "Extra arguments to pass to Slambda (nothing to see here right now).";
    };
  };

  config = lib.mkIf cfg.enable {
    environment.systemPackages = [ cfg.package ];

    users.groups.uinput = { };
    users.groups.slambda = { };

    users.users.slambda = {
      description = "Slambda system user.";
      group = "slambda";
      isSystemUser = true;
    };

    services.udev.extraRules = ''
      # Slambda user access to /dev/uinput
      KERNEL=="uinput", MODE="0660", GROUP="uinput", OPTIONS+="static_node=uinput"
    '';

    systemd.paths =
      builtins.listToAttrs
        (map mkPath (builtins.attrValues cfg.keyboards));

    systemd.services =
      builtins.listToAttrs
        (map mkService (builtins.attrValues cfg.keyboards));
  };
}
