import subprocess
import requests
import re
import shlex

releases_url = "https://raw.githubusercontent.com/rust-lang/rust/master/RELEASES.md"
result = requests.get(releases_url).text
versions = re.findall(r"^Version\s+(.*)\s+\(.*\)$", result, re.MULTILINE)
versions = versions[versions.index('1.67.1'):versions.index('1.50.0')]
for version in versions:
    subprocess.run(shlex.split(f'rbs sign_stdlib  -p release --provider IDA -t {version}-x86_64-unknown-linux-gnu'))