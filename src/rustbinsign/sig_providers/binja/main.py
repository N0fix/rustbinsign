import sys
from pathlib import Path
from typing import List, Optional
from pathlib import Path

# With this, we can at least test that the provider works
# even if the API isn't installed (probably...)
try:
    from binaryninja.warp import *
    BINJA_LOADED = True
except ImportError:
    BINJA_LOADED = False

class SignatureError(Exception):
    def __init__(self, message):
        super().__init__(message)


class BinjaProvider(BaseSigProvider:
    output_dir: Path
    def __init__(output_dir: Optional[str]):
        """
        Construct new BinjaProvider w/ optional output directory. Set to `./outputs` if not provided.
        """
        binaryninja._init_plugins()
        self.output_dir = Path("outputs")
        if output_dir != None:
            self.output_dir = Path(output_dir)
    def generate_signature(
        self, 
        libs: List[Path], 
        sig_name: Optional[str]) 
    -> Path:
        """
        Take some list of paths (files to generate WARP data for) and return path to output directory of generated WARP data
        
        Nothing is multithreaded here since Binja should be able to handle that (?).
        
        Basically inlined the simple Python API example (https://github.com/Vector35/binaryninja-api/blob/dev/plugins/warp/examples/create_signatures.py) here to not create a new WarpProcessor on each run
        """
        if not BINJA_LOADED:
            raise SignatureError("Binja API was not loaded or couldn't be found! Is it installed properly?")
        output_dir.mkdir(parents=True, exist_ok=True)
        processor = WarpProcessor()
        for lib in libs:
            output_file = output_dir / f"{lib.stem}.warp"
            # Unsure if it is possible to add all paths first then start processing.
            # start() returns a single WarpFile though so if one fails, everything fails maybe?
            processor.add_path(str(lib))
            file = processor.start()
            if not file:
                print(f"Failed to process {lib}! Continuing with remaining files...")
                continue
            buffer = file.to_data_buffer()
            with open(output_file, 'wb') as f:
                f.write(bytes(buffer))
            print(f"Wrote {len(buffer)} bytes to {output_file}")
