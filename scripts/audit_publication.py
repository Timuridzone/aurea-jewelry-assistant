"""Check tracked publication files for accidental secrets and local runtime data.

This focused heuristic check does not replace a full security review.
"""
import re
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
names = subprocess.check_output(['git', 'ls-files', '-z'], cwd=root).decode().split('\0')
patterns = {
    'private key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'GitHub credential': re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b'),
    'provider credential': re.compile(r'\bsk-[A-Za-z0-9_-]{20,}\b'),
    'AWS access key': re.compile(r'\bAKIA[A-Z0-9]{16}\b'),
    'local home path': re.compile(r'/(?:Users|home)/[A-Za-z0-9_.-]+/'),
}
failures = []
checked = 0
for name in filter(None, names):
    path = root / name
    if any(part in {'.venv', '__pycache__', '.pytest_cache', 'data'} for part in Path(name).parts) or (Path(name).name.startswith('.env') and Path(name).name != '.env.example') or re.search(r'\.(?:db|sqlite3?)(?:-|$)', name):
        failures.append(f'{name}: local runtime or environment file')
    if path.suffix.lower() in {'.jpg', '.jpeg', '.png'}:
        continue
    try:
        body = path.read_text()
    except (UnicodeError, OSError):
        failures.append(f'{name}: unexpected unreadable or binary file')
        continue
    checked += 1
    for label, pattern in patterns.items():
        if pattern.search(body):
            failures.append(f'{name}: possible {label}')
if failures:
    raise SystemExit('\n'.join(failures))
print(f'Publication audit passed: {checked} text files checked; no matched credential patterns or tracked runtime data.')
