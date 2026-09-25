"""Runtime version.

Injected at Docker build time via the SPIIK_VERSION build arg (the
release workflow passes the git tag). Outside Docker it falls back to
"dev" so local runs and tests never pretend to be a release.
"""

from __future__ import annotations

import os

VERSION = os.environ.get("SPIIK_VERSION", "dev")
