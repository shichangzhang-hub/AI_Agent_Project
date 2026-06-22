# ERR_OS_DEP Deployment Failure

## Symptoms

- Build or deployment fails with `ERR_OS_DEP`.
- The runtime image starts, but the process exits before the health check passes.
- Logs mention a missing shared library or missing system package.

## Typical Root Cause

`ERR_OS_DEP` usually means the application depends on an OS-level package that is not installed in the target environment. Common examples are `libpq`, `libssl`, `build-essential`, or image-processing libraries.

## Recommended Checks

1. Compare the dependency list between the local machine and the deployed host.
2. Check whether the base image changed recently.
3. Review the last successful deployment and diff the Dockerfile or build script.

## Safe Remediation Pattern

- Reinstall the missing package in the image or VM provisioning script.
- Rebuild the artifact after the package is present.
- Re-run the deployment and verify the health check.
