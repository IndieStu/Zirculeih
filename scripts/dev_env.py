"""Generate local development secrets once; never overwrite existing configuration."""

import secrets
from pathlib import Path

path = Path(".env")
if path.exists():
    raise SystemExit(".env exists; refusing to overwrite")
text = Path(".env.example").read_text()
text = text.replace("GENERATE_A_RANDOM_SECRET", secrets.token_urlsafe(64))
text = text.replace("GENERATE_A_DATABASE_PASSWORD", secrets.token_urlsafe(32))
with path.open("x") as stream:
    stream.write(text)
path.chmod(0o600)
print("Created private .env for local development")
