# Restart Loop After Config Change

## Symptoms

- Service containers restart repeatedly after a configuration rollout.
- The deployment controller reports failing probes.
- Application logs show missing environment variables or malformed JSON config.

## Typical Root Cause

A restart loop after a config change is often caused by a missing required variable, invalid JSON in an environment variable, or a mismatch between the expected config schema and the deployed value.

## Recommended Checks

1. Inspect the effective environment variables for the service.
2. Compare the new config against the last known-good release.
3. Validate JSON-formatted variables before restarting dependent services.
