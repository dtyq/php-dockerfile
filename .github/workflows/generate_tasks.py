import os
import json
from packaging.version import parse as parse_version

from misc import alpinePHPPackageSuffix, getHEADRev

phpAlpineVersions = {
    "8.5": "3.24",
    "8.4": "3.24",
    "8.3": "3.24",
    "8.2": "3.22",
    "8.1": "3.18",
}

extVersions = [
    # swoole master branch
    ("swoole", "master", "8.2", "8.6"),
    # swoole 6.2 branch
    ("swoole", "v6.2.6", "8.2", "8.5"),
    # swoole 6.1 branch
    ("swoole", "v6.1.13", "8.1", "8.4"),
    # swoole 6.0 branch
    ("swoole", "v6.0.2", "8.1", "8.4"),
    # swoole 5.1 branch
    ("swoole", "v5.1.8", "8.0", "8.3"),
    # swoole 5.0 branch
    ("swoole", "v5.0.3", "8.0", "8.2"),
    # swoole 4.8 branch
    ("swoole", "v4.8.13", "8.0", "8.2"),
    # swow ci branch
    ("swow", "ci", "8.1", None),
    # swow
    ("swow", "v2.0.0", "8.1", "8.6"),
]


githubOutput = open(os.environ["GITHUB_OUTPUT"], "w")

tasks = []
for phpVer, alpineVer in phpAlpineVersions.items():
    for extVersion in extVersions:
        ext, extRef, minPhpVer, maxPhpVer = extVersion
        if minPhpVer and parse_version(phpVer) < parse_version(minPhpVer):
            continue
        if maxPhpVer and parse_version(phpVer) > parse_version(maxPhpVer):
            continue

        if ext == "swoole":
            extRev = getHEADRev("swoole/swoole-src", extRef)
            extUrl = f"https://github.com/swoole/swoole-src/archive/{extRev}.tar.gz"
            extDev = f"libpq-dev c-ares-dev curl-dev openssl-dev libstdc++"
        elif ext == "swow":
            extRev = getHEADRev("swow/swow", extRef)
            extUrl = f"https://github.com/swow/swow/archive/{extRev}.tar.gz"
            extDev = f"libpq-dev curl-dev openssl-dev"
        else:
            raise Exception(f"not implemented: {ext}")
        if extRef == "master":
            extVer = "master"
        elif extRef == "ci":
            extVer = "ci"
        else:
            extVer = extRef.removeprefix("v")
        tag = f"{phpVer}-alpine-{alpineVer}-{ext}-{extVer}"

        task = {}
        task["args"] = "\n".join(
            [
                f"ALPINE_VERSION={alpineVer}",
                f"PHP_VERSION={phpVer}",
                f"ALPINE_PHP_PACKAGE_SUFFIX={alpinePHPPackageSuffix(alpineVer, phpVer)}",
                f"EXT_URL={extUrl}",
                f"EXT_REV={extRev}",
                f"EXT_DEV={extDev}",
                f"MIRROR={os.environ['PUBLIC_MIRROR']}",
            ]
        )
        task["tag"] = tag
        if parse_version(alpineVer) >= parse_version("3.22"):
            task["platforms"] = f"linux/amd64,linux/arm64,linux/riscv64"
        else:
            task["platforms"] = f"linux/amd64,linux/arm64"
        tasks.append(task)

print(f"generated tasks: {json.dumps(tasks, indent=2)}")
githubOutput.write(f"tasks={json.dumps(tasks)}\n")

githubOutput.close()
