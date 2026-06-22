# Windows Dependency Checks

## Useful Read-Only Commands

- `Get-ChildItem Env:` to inspect environment variables.
- `where python` to verify command resolution.
- `python --version` to confirm runtime availability.
- `pip list` to inspect installed Python packages.
- `Test-Path <path>` to verify whether an expected file exists.

## Notes

These commands are safe for a diagnostic assistant because they read local state without mutating the machine. They are good first steps before suggesting a repair script.
