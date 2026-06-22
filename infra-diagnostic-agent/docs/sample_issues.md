# Sample Issues

These sample issues are written to sound closer to real enterprise incidents than short toy prompts.

## 1. Deployment Failure After Base Image Update

Use when you want to demonstrate:

- RAG retrieval for platform and build incidents
- The Agent converging on an OS-level dependency problem

Prompt:

`Deployment failed with ERR_OS_DEP after the new image rollout. The container exits before health checks pass, and the logs mention a missing shared library.`

Expected direction:

- Retrieve `err_os_dep.md`
- Infer that the new runtime image is likely missing an OS package
- Suggest checking base image changes and reinstalling the missing package

## 2. Payment Requests Fail After Auth Change

Use when you want to demonstrate:

- Cross-service reasoning language
- Why internal postmortems and architecture knowledge matter

Prompt:

`Since this morning, checkout requests return 401 even though the payment service health check is green. We rotated authentication keys last night and now only payment traffic is failing.`

Expected direction:

- Retrieve `payment_auth_failure.md`
- Infer that the payment service depends on a lower-level auth component
- Suggest validating key rotation, auth package changes, or token verification rules

## 3. Restart Loop After Configuration Rollout

Use when you want to demonstrate:

- Config-driven production incidents
- Controlled system inspection plus doc lookup

Prompt:

`After yesterday's config rollout, one of our services is stuck in a restart loop. Probes fail, and the application log says a required environment variable is missing or malformed.`

Expected direction:

- Retrieve `restart_loop_after_config_change.md`
- Suggest validating effective environment variables and checking JSON config formatting
- Optionally inspect local environment paths with safe read-only commands

## 4. Windows Host Dependency Inspection

Use when you want to demonstrate:

- The safe command executor
- Why the project does not blindly execute repair scripts

Prompt:

`A developer machine cannot run the local service because Python and some dependencies may not be on PATH. Please diagnose with safe checks only.`

Expected direction:

- Use `windows_dependency_checks.md`
- Run read-only commands such as `where python`, `python --version`, or `pip list`
- Return a diagnosis instead of mutating the host
