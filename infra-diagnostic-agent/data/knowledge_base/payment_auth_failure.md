# Payment Service Authentication Failure

## Symptoms

- Payment requests fail with `401` or `403`.
- The payment service health check stays green, but checkout requests fail.
- Logs show token validation or signature verification errors.

## Typical Root Cause

The payment service often depends on a lower-level authentication component. If the core auth library rotates keys or changes token validation rules, payment calls can fail even when the payment service itself has not changed.

## Investigation Hints

1. Check whether the authentication service or shared auth package changed in the last deployment window.
2. Search internal postmortems for key rotation incidents.
3. Confirm whether multiple services started failing at the same time.

## Safe Remediation Pattern

- Roll back the auth package or restore the expected signing key.
- Restart only the affected upper-layer services after the auth dependency is healthy.
