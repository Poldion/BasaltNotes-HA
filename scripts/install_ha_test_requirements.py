"""Install the requirements of the HA integrations basaltnotes depends on.

pytest-homeassistant-custom-component installs Home Assistant, but not the
requirements of conversation and its dependencies. Read them from the
installed manifests so they always match the Home Assistant version.
"""

import json
from pathlib import Path
import subprocess
import sys

import homeassistant.components

COMPONENTS = Path(homeassistant.components.__file__).parent
DOMAINS = ["conversation", "intent", "http", "media_source", "stream", "ffmpeg"]

requirements = sorted(
    {
        requirement
        for domain in DOMAINS
        if (manifest := COMPONENTS / domain / "manifest.json").exists()
        for requirement in json.loads(manifest.read_text()).get("requirements", [])
    }
)
print("Installing", " ".join(requirements))
subprocess.check_call([sys.executable, "-m", "pip", "install", *requirements])
