import pathlib
from abc import ABC
from typing import List, Optional


class BaseSigProvider(ABC):
    def generate_signature(
        self, libs: List[pathlib.Path], sig_name: Optional[str]
    ) -> pathlib.Path:
        ...
