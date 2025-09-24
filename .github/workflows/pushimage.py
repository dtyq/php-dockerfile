#!/usr/bin/env python3

import sys
import os
import json
import subprocess
import re
from typing import Union

AUTH_FILE = os.path.expanduser("~/.docker/config.json")
imageNameRe = re.compile(r"^(?P<registry>[^/]+)/(?P<image>[^:@]+)$")


def exec(cmd: list[str], capture_output: bool = False) -> Union[int, bytes]:
    print(f"\033[1mexecuting {cmd}\033[0m", file=sys.stderr)
    proc = subprocess.run(cmd, capture_output=capture_output)
    if proc.returncode != 0:
        print(f"\033[31mfailed to execute {cmd}\033[0m", file=sys.stderr)
        if capture_output:
            print(f"\033[31merror: {proc.stderr.decode()}\033[0m", file=sys.stderr)
        return proc.returncode
    return proc.stdout if capture_output else 0


def pushimage(tag: str, images: list[str]) -> None:
    dockerArch = {
        "x86_64": "amd64",
        "aarch64": "arm64",
    }[os.uname().machine]
    imageName = os.environ["IMAGE_NAME"]
    digests = {}
    for image in images:
        for t in (tag, f"{tag}-debuggable"):
            # retag source image to single arch image
            if (
                exec(["docker", "tag", f"{imageName}:{t}", f"{image}:{t}-{dockerArch}"])
                != 0
            ):
                print(
                    f"\033[31mfailed to tag {imageName}:{t} to {image}:{t}-{dockerArch}\033[0m",
                    file=sys.stderr,
                )
                continue

            # push single arch image
            if exec(["docker", "push", f"{image}:{t}-{dockerArch}"]) != 0:
                print(
                    f"\033[31mfailed to push {image}:{t}-{dockerArch}\033[0m",
                    file=sys.stderr,
                )
                continue

            # get single arch image digest
            singleImageInfoBytes = exec(
                ["docker", "image", "inspect", f"{image}:{t}-{dockerArch}"],
                capture_output=True,
            )
            if isinstance(singleImageInfoBytes, bytes):
                singleImageInfo = json.loads(singleImageInfoBytes.decode())
            else:
                print(
                    f"\033[31mfailed to get single arch image digest {image}:{t}-{dockerArch}\033[0m",
                    file=sys.stderr,
                )
                continue

            # find this build digest
            thisBuildDigest = None
            if image.startswith(f"index.docker.io/"):
                thisBuildDigest = singleImageInfo[0]["RepoDigests"][0].split("@")[1]
            else:
                for repoDigest in singleImageInfo[0]["RepoDigests"]:
                    if repoDigest.startswith(f"{image}@"):
                        thisBuildDigest = repoDigest.split("@")[1]
                        break
            if thisBuildDigest is None:
                print(
                    f"\033[31mfailed to find this build digest {image}:{t}-{dockerArch}\033[0m",
                    file=sys.stderr,
                )
                continue

            # add single arch image digest to digests
            digests[f"{image}:{t}-{dockerArch}"] = thisBuildDigest

            # get multi arch image digest
            multiManifestBytes = exec(
                ["docker", "manifest", "inspect", f"{image}:{t}"],
                capture_output=True,
            )
            if isinstance(multiManifestBytes, bytes):
                multiManifest = json.loads(multiManifestBytes.decode())
                if (
                    multiManifest["mediaType"]
                    != "application/vnd.oci.image.index.v1+json"
                    and multiManifest["mediaType"]
                    != "application/vnd.docker.distribution.manifest.list.v2+json"
                ):
                    # it's a single arch image, make it a index
                    if (
                        exec(
                            [
                                "docker",
                                "manifest",
                                "create",
                                f"{image}:{t}",
                                f"{image}@{thisBuildDigest}",
                            ]
                        )
                        != 0
                    ):
                        print(
                            f"\033[31mfailed to create manifest {image}:{t}\033[0m",
                            file=sys.stderr,
                        )
                        continue

                    multiManifestBytes = exec(
                        ["docker", "manifest", "inspect", f"{image}:{t}"],
                        capture_output=True,
                    )
                    if isinstance(multiManifestBytes, bytes):
                        multiManifest = json.loads(multiManifestBytes.decode())
                    else:
                        print(
                            f"\033[31mfailed to get multi arch image digest {image}:{t}\033[0m",
                            file=sys.stderr,
                        )
                        continue

                archImages = {
                    manifest["platform"]["architecture"]: manifest["digest"]
                    for manifest in multiManifest["manifests"]
                }
                archImages[dockerArch] = thisBuildDigest

                exec(["docker", "manifest", "rm", f"{image}:{t}"])

                if (
                    exec(
                        [
                            "docker",
                            "manifest",
                            "create",
                            f"{image}:{t}",
                            *[f"{image}@{digest}" for digest in archImages.values()],
                        ]
                    )
                    != 0
                ):
                    print(
                        f"\033[31mfailed to create manifest {image}:{t}\033[0m",
                        file=sys.stderr,
                    )
                    continue
                # fixme: debug
                exec(["docker", "manifest", "inspect", f"{image}:{t}"])
                if exec(["docker", "manifest", "push", f"{image}:{t}"]) != 0:
                    print(f"\033[31mfailed to push {image}:{t}\033[0m", file=sys.stderr)
                    continue
            else:
                # image may not exist, just override it
                if (
                    exec(
                        [
                            "docker",
                            "manifest",
                            "create",
                            f"{image}:{t}",
                            f"{image}@" + singleManifest["config"]["digest"],
                        ]
                    )
                    != 0
                ):
                    print(
                        f"\033[31mfailed to create manifest {image}:{t}\033[0m",
                        file=sys.stderr,
                    )
                    continue
                if exec(["docker", "manifest", "push", f"{image}:{t}"]) != 0:
                    print(f"\033[31mfailed to push {image}:{t}\033[0m", file=sys.stderr)
                    continue

    githubOutput = open(os.environ["GITHUB_OUTPUT"], "w")
    githubOutput.write(f"${{ matrix.tag.outputVar }}={json.dumps(digests)}\n")
    githubOutput.close()


if __name__ == "__main__":
    tag = sys.argv[1]
    images = json.loads(sys.argv[2])
    pushimage(tag, images)
