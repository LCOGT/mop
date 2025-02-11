# Microlensing Observation Portal

TOM Toolkit for the LCO microlensing team. We harvest, fit, rank and observe all events in the sky!
To join the team, please contact etibachelet@gmail.com and/or rstreet@lco.global.

## Development (w/ Kuberentes)

Always enter the development shell before doing anything else. This will make
sure everyone is using the same version of tools, to avoid any system discrepancies.

Install [Nix](https://github.com/LCOGT/public-wiki/wiki/Install-Nix) if you have
not already.

If you have [direnv](https://github.com/LCOGT/public-wiki/wiki/Install-direnv)
installed, the shell will automatically activate and deactive anytime you change
directories. You may have to grant permissions initially with:

```sh
direnv allow
```

Otherwise, you can manually enter the shell with:

```sh
./develop.sh
```

Spin up dependencies:

```sh
skaffold -m mop-deps run
```

Start development loop:

```sh
skaffold -m mop dev
```

This will watch source-code files for any changes and re-deploy automatically
when they are modified.

If you don't want that behaviour, you can also just have it run in the background:

```sh
skaffold -m mop run
```

MOP should be running at https://mop.local.lco.earth

### Clean-up

You can delete all resources deployed by skaffold with:

```sh
skaffold -m mop,mop-deps delete
```

## Build

This project is built automatically by the [LCO Jenkins Server](http://jenkins.lco.gtn/).
Please see the [Jenkinsfile](Jenkinsfile) for further details.

## Production Deployment

This project is deployed to the LCO Kubernetes Cluster. Please see the
[LCO Helm Charts Repository](https://github.com/LCOGT/helm-charts) for further
details.

## License

This project is licensed under the GNU GPL v3. Please see the [LICENSE](LICENSE)
file for further details.
