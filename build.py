#!/usr/bin/env python

import os, sys, re, subprocess, socket

tagRe = re.compile(
    r"^(?P<phpver>\d\.\d)-alpine-(?P<alpinever>(?:\d\.\d+|edge))-(?P<ext>swow|swoole)-(?P<extver>\d+\.\d+\.\d+(?:-alpha(?:\.\d+)*)*(?:-nightly\d+)*)(?P<exts>(?:-[^-]+)*)$"
)

imageName = os.environ.get("IMAGE_NAME")

if not imageName:
    raise Exception("IMAGE_NAME 环境变量未设置")

tryMirrors = os.environ.get(
    "TRY_MIRRORS", "http://mirrors.cloud.aliyuncs.com,http://mirrors.tencentyun.com"
).split(",")


publicMirror = os.environ.get("PUBLIC_MIRROR", "https://mirrors.ustc.edu.cn")


def mian(argv0, tag, *args):
    match = tagRe.match(tag)
    if not match:
        raise Exception(f"错误的tag格式，用法：{argv0} <tag>")

    groups = match.groupdict()
    if groups["exts"]:
        sortedExts = "-" + "-".join(
            sorted(filter(lambda x: bool(x), groups["exts"].split("-")))
        )
        if sortedExts != groups["exts"]:
            raise Exception(f"附加扩展们没有按照字母表排序，应更改为{sortedExts}")

    for ext in filter(lambda x: bool(x), groups["exts"].split("-")):
        if not os.path.isfile(f"exts/{ext}.sh"):
            raise Exception(f"不支持的附加扩展{ext}，联系这个仓库的维护者")

    if groups["ext"] == "swoole":
        extUrl = (
            f"https://github.com/swoole/swoole-src/archive/v{groups['extver']}.tar.gz"
        )
        extDev = f"libpq-dev c-ares-dev curl-dev openssl-dev libstdc++"
    elif groups["ext"] == "swow":
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

    fullTag = f"{imageName}:{tag}"

    if groups["exts"]:
        extsBuildArg = (
            "--build-arg",
            f"EXTS={groups['exts']}",
        )
    else:
        extsBuildArg = ()

    print("构建无符号（镜像比较小，生产用）版本")
    args = [
        "docker",
        "buildx",
        "build",
        "-t",
        fullTag,
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
        f"EXT_URL={extUrl}",
        "--build-arg",
        f"EXT_DEV={extDev}",
        "--build-arg",
        f"MIRROR={mirror}",
        "--build-arg",
        f"CURL_PROXY={proxy}",
        *extsBuildArg,
        ".",
    ]
    print(args)
    strippedBuild = subprocess.Popen(args=args, stdout=sys.stdout, stderr=sys.stderr)
    strippedBuild.wait()
    if strippedBuild.returncode != 0:
        raise Exception("构建无符号版本失败")

    print("构建有符号（镜像比较大，调试/带符号生产用）版本")
    args = [
        "docker",
        "buildx",
        "build",
        "-t",
        f"{fullTag}-debuggable",
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
        f"EXT_URL={extUrl}",
        "--build-arg",
        f"EXT_DEV={extDev}",
        "--build-arg",
        f"MIRROR={mirror}",
        "--build-arg",
        f"CURL_PROXY={proxy}",
        *extsBuildArg,
        ".",
    ]
    print(args)
    debuggableBuild = subprocess.Popen(args=args, stdout=sys.stdout, stderr=sys.stderr)
    debuggableBuild.wait()
    if debuggableBuild.returncode != 0:
        raise Exception("构建有符号版本失败")

if __name__ == "__main__":
    exit(mian(*sys.argv))
