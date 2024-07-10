from typing import Dict, Optional

from pydantic import BaseModel

from .logger import logger as log


class Config(BaseModel):
    # target: pathlib.Path
    ...


class CompilationCtx(BaseModel):
    profile: str = "release"
    template: Optional[Dict] = {
        "lib": {"crate-type": ["dylib"]},
        "profile": {
            "release": {"debug": 2, "panic": "abort", "strip": "none"},  # Usefull for no-std crates
            "dev": {"debug": 2, "panic": "abort", "strip": "none"},  # Usefull for no-std crates
        },
    }
    lib: bool = True
    env: Optional[dict] = {}  # Additional env variable to use compile time
