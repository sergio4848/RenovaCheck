# Extra CA certificates for image builds

Images copy every file in this directory into the system trust store during the build
(build context `certs`, see `compose.yaml`). Use it only when the build host sits behind a
TLS-intercepting proxy: put the proxy's CA as a `*.crt` file here. `*.crt` files are
git-ignored and never committed.
