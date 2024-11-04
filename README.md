# Microlensing Observation Portal

TOM Toolkit for the LCO microlensing team. We harvest, fit, rank and observe all events in the sky!
To join the team, please contact etibachelet@gmail.com and/or rstreet@lco.global.

## Development (w/ Kuberentes)

Install [Nix](https://github.com/LCOGT/public-wiki/wiki/Install-Nix) and then
enter the development environment:

```shell
nix develop --impure
```

Start a local development K8s cluster and container registry:

```shell
ctlptl apply -f ./local-registry.yaml -f ./local-cluster.yaml
```

Spin up dependencies:

```shell
skaffold -m mop-deps run
```

Start development loop:

```shell
skaffold -m mop dev
```

This will watch source-code files for any changes and re-deploy automatically
when they are modified.

The application will be port-forwarded to a port listed in the logs:

```
...
Deployments stabilized in 13.077 seconds
Port forwarding Service/server in namespace mop, remote port http -> http://127.0.0.1:4503
Listing files to watch...
 - mop
Press Ctrl+C to exit
...
```

### Clean-up

You can simply delete the application specific development cluster to clean everything up:

```shell
ctlptl delete -f ./local-cluster.yaml
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
