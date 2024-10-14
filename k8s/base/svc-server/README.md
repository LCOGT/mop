# service

## Description

This package provides a bare-bones [`v1.Service`](https://kubernetes.io/docs/concepts/services-networking/service/)
that you can build upon and use in other packages.

## Usage

Clone this package:

```shell
kpt pkg get https://github.com/LCOGT/kpt-pkg-catalog/service svc-myname
```

Customize `svc.yaml`:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: example
spec:
  type: ClusterIP
  selector:
    app.kubernetes.io/component: test # <-- Target Pods with this label
  ports:
    - name: something
      port: 1234
      targetPort: container-port-name
```

And then render to update resources:

```shell
kpt fn render
```

This package is also a Kustomization, so it can also be referenced by other
Kustomizations:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - ./svc-myname/
```
