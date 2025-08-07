{
  description = "We harvest, fit, rank and observe all events in the sky!";

  inputs = {
    devenv-k8s.url = "github:LCOGT/devenv-k8s";

    nixpkgs.follows = "devenv-k8s/nixpkgs";
    flake-parts.follows = "devenv-k8s/flake-parts";
  };

  nixConfig = {
    extra-substituters = [
      "https://devenv.cachix.org"
      "https://lco-public.cachix.org"
    ];

    extra-trusted-public-keys = [
      "devenv.cachix.org-1:w1cLUi8dv3hnoSPGAuibQv+f9TZLr6cv/Hm9XgU50cw="
      "lco-public.cachix.org-1:zSmLK7CkAehZ7QzTLZKt+5Y26Lr0w885GUB4GlT1SCg="
    ];
  };

  outputs = inputs@{ flake-parts, ... }:
    flake-parts.lib.mkFlake { inherit inputs; } {
      imports = [
        inputs.devenv-k8s.flakeModules.default
      ];

      systems = [ "x86_64-linux" "aarch64-linux" "aarch64-darwin" "x86_64-darwin" ];

      perSystem = { config, self', inputs', pkgs, system, ... }: {
        # Per-system attributes can be defined here. The self' and inputs'
        # module parameters provide easy access to attributes of the same
        # system.

        # https://devenv.sh/basics/
        # Enter using `nix develop --impure`
        config.devenv.shells.default = {
          languages.python = {
            enable = true;
            package = pkgs.python310;

            poetry = {
              enable = true;
              install.enable = true;
              activate.enable = true;
            };
          };

          # https://devenv.sh/packages/
          packages = [
              # Needed to build psycopg2
              pkgs.postgresql
              pkgs.libpqxx
          ];

          # https://devenv.sh/reference/options/#entershell
          enterShell = ''
            export KUBECONFIG="`pwd`/local-kubeconfig"

            echo "Setting KUBECONFIG=$KUBECONFIG"
            echo
            echo "This is done to sandbox Kuberenetes tools (kubectl, skaffold, etc) to the local K8s cluster for this project."
            echo "If you would like to use a local K8s cluster across multiple projects, then set 'KUBECONFIG' to a common path"
            echo "in both projects before running the command to create the local cluster."

            cp --no-clobber $DEVENV_ROOT/k8s/envs/local/secrets.env.changeme $DEVENV_ROOT/k8s/envs/local/secrets.env
            echo
            echo "Configure application environment variables in '$DEVENV_ROOT/k8s/envs/local/secrets.env'"
          '';
        };
      };

      flake = {
        # The usual flake attributes can be defined here, including system-
        # agnostic ones like nixosModule and system-enumerating ones, although
        # those are more easily expressed in perSystem.

      };
    };
}
