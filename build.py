#!/usr/bin/env python3

import os
import sys
import re
import subprocess
import socket
import argparse

from misc import alpinePHPPackageSuffix, getHEADRev

tagRe = re.compile(
    r"^(?P<phpver>\d\.\d)-alpine-(?P<alpinever>(?:\d\.\d+|edge))-(?P<ext>swow|swoole)-(?P<extver>\d+\.\d+\.\d+(?:-alpha(?:\.\d+)*)*(?:-nightly\d+)*|ci|master)$"
)

tryMirrors = os.environ.get(
    "TRY_MIRRORS", "http://mirrors.cloud.aliyuncs.com,http://mirrors.tencentyun.com"
).split(",")


publicMirror = os.environ.get("PUBLIC_MIRROR", "https://mirrors.ustc.edu.cn")


def mian():
    parser = argparse.ArgumentParser()
    parser.add_argument("TAG", help="tag, see README.md for tag naming convention")
    parser.add_argument("IMAGE_NAMES", nargs="+", help="image names")
    parser.add_argument("--oci", action="store_true", help="export to oci format")
    parser.add_argument("--gen-metadata", help="generate metadata", action="store_true")
    parser.add_argument("--push", action="store_true", help="push to registry")
    parser.add_argument(
        "--arch-suffix", action="store_true", help="add arch suffix to image name"
    )
    args = parser.parse_args()

    tag = args.TAG
    match = tagRe.match(args.TAG)
    if not match:
        raise Exception(f"错误的tag格式")

    groups = match.groupdict()
    if groups["ext"] == "swoole":
        if groups["extver"] == "ci":
            raise Exception("swoole不使用ci分支")
        elif groups["extver"] == "master":
            extRev = getHEADRev("swoole/swoole-src", "master")
            extUrl = f"https://github.com/swoole/swoole-src/archive/{extRev}.tar.gz"
        else:
            extRev = getHEADRev("swoole/swoole-src", "v" + groups["extver"])
            extUrl = f"https://github.com/swoole/swoole-src/archive/v{groups['extver']}.tar.gz"
        extDev = f"libpq-dev c-ares-dev curl-dev openssl-dev libstdc++"
    elif groups["ext"] == "swow":
        if groups["extver"] == "master":
            raise Exception("swow不使用master分支")
        elif groups["extver"] == "ci":
            extRev = getHEADRev("swow/swow", "ci")
            extUrl = f"https://github.com/swow/swow/archive/{extRev}.tar.gz"
        else:
            extRev = getHEADRev("swow/swow", "v" + groups["extver"])
            extUrl = f"https://github.com/swow/swow/archive/v{groups['extver']}.tar.gz"
        extDev = f"libpq-dev curl-dev openssl-dev"
    else:
        raise Exception("not implemented")

    mirror = publicMirror
    for m in tryMirrors:
        if not m:
            continue
        domain = m.removeprefix("https://").removeprefix("http://")
        try:
            socket.getaddrinfo(domain, 80)
            mirror = m
            break
        except Exception:
            pass
    print(f"使用镜像{mirror}")

    proxy = os.getenv("https_proxy") or ""
    print(f"proxy={proxy}")

    dockerArch = {
        "x86_64": "amd64",
        "aarch64": "arm64",
    }[os.uname().machine]

    fullTagArgs = []
    for imageName in args.IMAGE_NAMES:
        fullTagArgs.append(f"-t")
        if args.arch_suffix:
            fullTagArgs.append(f"{imageName}:{tag}-{dockerArch}")
        else:
            fullTagArgs.append(f"{imageName}:{tag}")

    if os.getenv("CI"):
        print("##[group]", end="")
    print("构建无符号（镜像比较小，生产用）版本")
    cmd = [
        "docker",
        "buildx",
        "build",
        *fullTagArgs,
        *(("--output=type=oci,dest=/dev/null",) if args.oci else ()),
        *(("--push",) if args.push else ("--load",)),
        *(("--metadata-file=metadata_stripped.json",) if args.gen_metadata else ()),
        "--pull",
        "--no-cache",
        "--force-rm",
        "--progress=plain",
        "--target",
        f"stripped",
        "--build-arg",
        f"ALPINE_VERSION={groups['alpinever']}",
        "--build-arg",
        f"PHP_VERSION={groups['phpver']}",
        "--build-arg",
        f"ALPINE_PHP_PACKAGE_SUFFIX={alpinePHPPackageSuffix(groups['alpinever'], groups['phpver'])}",
        "--build-arg",
        f"EXT_URL={extUrl}",
        "--build-arg",
        f"EXT_REV={extRev}",
        "--build-arg",
        f"EXT_DEV={extDev}",
        "--build-arg",
        f"MIRROR={mirror}",
        "--build-arg",
        f"CURL_PROXY={proxy}",
        ".",
    ]
    print(cmd)
    strippedBuild = subprocess.Popen(args=cmd, stdout=sys.stdout, stderr=sys.stderr)
    strippedBuild.wait()
    if strippedBuild.returncode != 0:
        raise Exception("构建无符号版本失败")

    if os.getenv("CI"):
        print("##[endgroup]")

    fullTagArgs = []
    for imageName in args.IMAGE_NAMES:
        fullTagArgs.append(f"-t")
        if args.arch_suffix:
            fullTagArgs.append(f"{imageName}:{tag}-debuggable-{dockerArch}")
        else:
            fullTagArgs.append(f"{imageName}:{tag}-debuggable")

    if os.getenv("CI"):
        print("##[group]", end="")
    print("构建有符号（镜像比较大，调试/带符号生产用）版本")
    cmd = [
        "docker",
        "buildx",
        "build",
        *fullTagArgs,
        *(("--output=type=oci,dest=/dev/null",) if args.oci else ()),
        *(("--push",) if args.push else ("--load",)),
        *(("--metadata-file=metadata_debuggable.json",) if args.gen_metadata else ()),
        # "--pull",
        # "--no-cache",
        "--force-rm",
        "--progress=plain",
        "--target",
        f"debuggable",
        "--build-arg",
        f"ALPINE_VERSION={groups['alpinever']}",
        "--build-arg",
        f"PHP_VERSION={groups['phpver']}",
        "--build-arg",
        f"ALPINE_PHP_PACKAGE_SUFFIX={alpinePHPPackageSuffix(groups['alpinever'], groups['phpver'])}",
        "--build-arg",
        f"EXT_URL={extUrl}",
        "--build-arg",
        f"EXT_REV={extRev}",
        "--build-arg",
        f"EXT_DEV={extDev}",
        "--build-arg",
        f"MIRROR={mirror}",
        "--build-arg",
        f"CURL_PROXY={proxy}",
        ".",
    ]
    print(cmd)
    debuggableBuild = subprocess.Popen(args=cmd, stdout=sys.stdout, stderr=sys.stderr)
    debuggableBuild.wait()
    if debuggableBuild.returncode != 0:
        raise Exception("构建有符号版本失败")

    if os.getenv("CI"):
        print("##[endgroup]")


if __name__ == "__main__":
    exit(mian())
