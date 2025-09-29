#!/usr/bin/env python3

import argparse
import sys
import os
import json
import subprocess
import re
from typing import Optional, Union
import urllib.parse
import base64
import logging

import requests
from urllib3 import response

# logging.basicConfig(level=logging.DEBUG)

SUPPORTED_ARCHS = ["amd64", "arm64"]

dockerConfigDict = json.load(open(os.path.expanduser("~/.docker/config.json")))
imageNameRe = re.compile(r"^(?P<registry>[^/]+)/(?P<image>[^:@]+)$")
challengeKVRe = re.compile(r'(?P<k>realm|service|scope)="(?P<v>[^"]+)",*')

tokens: dict[str, str] = {}


logging.basicConfig(level=logging.INFO)


def request(
    registry: str,
    path: str,
    method: str = "GET",
    headers: dict = None,
    data: dict = None,
) -> requests.Response:
    global tokens
    if not headers:
        headers = {}

    url = f"https://{registry}{path}"
    response = requests.request(method, url, headers=headers, json=data)
    if response.status_code == 401:
        challenge = response.headers.get("WWW-Authenticate").removeprefix("Bearer ")

        # if we have a token for this challenge, use it
        if tokens.get(challenge):
            headers["Authorization"] = f"Bearer {tokens[challenge]}"
            response = requests.request(method, url, headers=headers, json=data)
            if response.status_code != 401:
                return response
            else:
                del tokens[challenge]

        # if we don't have a token for this challenge, get one
        if registry == "index.docker.io":
            registry = "https://index.docker.io/v1/"
        if not dockerConfigDict.get("auths", {}).get(registry):
            raise Exception(
                f"no credentials for {registry} but authentication required"
            )
        base64Cred = dockerConfigDict["auths"][registry]["auth"]

        # parse challenge
        challengeDict = {}
        for m in challengeKVRe.finditer(challenge):
            challengeDict[m.group("k")] = m.group("v")
        # print(f"challengeDict: {challengeDict}")
        realm = challengeDict.get("realm")
        if not realm:
            raise Exception(f"failed to parse challenge: {challenge}")
        realm = challengeDict["realm"].rstrip("/")
        oauthURL = (
            realm
            + "?"
            + "&".join(
                [f"{k}=" + urllib.parse.quote_plus(v) for k, v in challengeDict.items()]
            )
        )
        # print(f"oauthURL: {oauthURL}")

        # get token
        response = requests.get(
            oauthURL,
            headers={
                "accept": "application/json",
                "authorization": f"Basic {base64Cred}",
            },
        )
        tokens[challenge] = response.json()["token"]
        headers["Authorization"] = f"Bearer {tokens[challenge]}"
        response = requests.request(method, url, headers=headers, json=data)
        return response

    return response


def toDockerArch(arch: str) -> str:
    return {
        "x86_64": "amd64",
        "aarch64": "arm64",
    }[arch]


class Manifest:
    manifestCache: dict[str, "Manifest"] = {}
    blobCache: dict[str, bytes] = {}

    def __init__(self, manifest: dict, size: int, digest: str):
        self.manifest = manifest
        self.size = size
        self.digest = digest

    @classmethod
    def getManifest(
        cls, registry: str, repository: str, ref: str
    ) -> Optional["Manifest"]:
        if ref in cls.manifestCache:
            return cls.manifestCache[ref]
        response = request(
            registry,
            f"/v2/{repository}/manifests/{ref}",
            headers={
                "Accept": "application/vnd.oci.image.index.v1+json, application/vnd.oci.image.manifest.v1+json, application/vnd.docker.distribution.manifest.v2+json, application/vnd.docker.distribution.manifest.list.v2+json"
            },
        )
        if response.status_code == 404:
            logging.debug(f"manifest {ref} for {repository} not found: {response.text}")
            return None
        if response.status_code != 200:
            raise Exception(
                f"failed to get manifest for {repository}:{ref} {response.status_code} {response.text}"
            )
        manifest = response.json()
        cls.manifestCache[ref] = cls(
            manifest,
            int(response.headers.get("content-length")),
            response.headers.get("docker-content-digest"),
        )
        return cls.manifestCache[ref]

    @classmethod
    def getBlob(cls, registry: str, repository: str, digest: str) -> Optional[bytes]:
        if digest in cls.blobCache:
            return cls.blobCache[digest]
        response = request(
            registry,
            f"/v2/{repository}/blobs/{digest}",
            headers={"Accept": "*"},
        )
        if response.status_code == 404:
            logging.debug(f"blob {digest} for {repository} not found: {response.text}")
            return None
        if response.status_code != 200:
            raise Exception(
                f"failed to get blob with digest {digest} for {repository} {response.status_code} {response.text}"
            )
        cls.blobCache[digest] = response.content
        return cls.blobCache[digest]

    @classmethod
    def invalidateManifestCache(cls, ref: str):
        if ref in cls.manifestCache:
            del cls.manifestCache[ref]

    def isIndex(self) -> bool:
        return (
            self.manifest["mediaType"] == "application/vnd.oci.image.index.v1+json"
            or self.manifest["mediaType"]
            == "application/vnd.docker.distribution.manifest.list.v2+json"
        )

    def toRefDict(self, **extra) -> dict:
        return {
            "mediaType": self.manifest["mediaType"],
            "digest": self.digest,
            "size": self.size,
            **extra,
        }


githubOutput = open(os.environ["GITHUB_OUTPUT"], "w")


def mergeimage(image: str, tag: str, digest: str) -> bool:
    m = imageNameRe.match(image)
    registry = m.group("registry")
    repository = m.group("image")
    dockerArch = toDockerArch(os.uname().machine)

    # get all single arch manifests
    singleArchManifests: dict[str, dict] = {}
    for arch in SUPPORTED_ARCHS:
        singleArchManifest = Manifest.getManifest(registry, repository, f"{tag}-{arch}")
        if singleArchManifest is None:
            logging.info(
                f"no single arch manifest for {registry}/{repository}:{tag}-{arch}"
            )
            continue
        if not singleArchManifest.isIndex():
            configBytes = Manifest.getBlob(
                registry, repository, singleArchManifest.manifest["config"]["digest"]
            )
            config = json.loads(configBytes)
            singleArchManifest = Manifest(
                {
                    "mediaType": "application/vnd.oci.image.index.v1+json",
                    "manifests": [
                        singleArchManifest.toRefDict(
                            platform={
                                "architecture": config["architecture"],
                                "os": config["os"],
                            }
                        ),
                    ],
                },
                0,
                "",
            )
        singleArchManifests[arch] = singleArchManifest

    if singleArchManifests[dockerArch].digest != digest:
        logging.error(
            f"single arch manifest for {registry}/{repository}:{tag}-{dockerArch} mismatch with digest {digest}, image upload failed"
        )
        return False

    # merge multi arch manifest with single arch manifest
    manifestRefs: list[dict] = []
    for arch, singleArchManifest in singleArchManifests.items():
        for manifestRef in singleArchManifest.manifest["manifests"]:
            manifestRefs.append(manifestRef)
            if arch and arch != "unknown":
                # try get github attestations for this arch
                attestTag = singleArchManifest.digest.replace(":", "-")
                attestManifest = Manifest.getManifest(registry, repository, attestTag)
                if attestManifest is None:
                    logging.info(
                        f"no github provenance attest manifest for {registry}/{repository}@{singleArchManifest.digest}"
                    )
                    continue
                if attestManifest.isIndex():
                    for manifestRef in attestManifest.manifest["manifests"]:
                        # github will use empty string as platform, so we need to set it to unknown
                        manifestRef["platform"] = {
                            "architecture": "unknown",
                            "os": "unknown",
                        }
                        manifestRefs.append(manifestRef)
                else:
                    manifestRefs.append(attestManifest.toRefDict())

    # create index manifest
    indexManifest = {
        "mediaType": "application/vnd.oci.image.index.v1+json",
        "schemaVersion": 2,
        "manifests": manifestRefs,
    }
    response = request(
        registry,
        f"/v2/{repository}/manifests/{tag}",
        method="PUT",
        headers={
            "Content-Type": "application/vnd.oci.image.index.v1+json",
        },
        data=indexManifest,
    )
    if response.status_code >= 300 or response.status_code < 200:
        logging.error(
            f"failed to push index manifest for {registry}/{repository}:{tag} {response.status_code} {response.text}"
        )
        return False
    multiArchDigest = response.headers["docker-content-digest"]
    logging.info(f"image {image}:{tag} created with digest: {multiArchDigest}")
    if tag.endswith("-debuggable"):
        if image.startswith("ghcr.io/"):
            githubOutput.write(f"ghcrDebuggableDigest={multiArchDigest}\n")
        elif image.startswith("index.docker.io/"):
            githubOutput.write(f"dockerhubDebuggableDigest={multiArchDigest}\n")
        elif image.startswith("public.ecr.aws/"):
            githubOutput.write(f"awsEcrDebuggableDigest={multiArchDigest}\n")
    else:
        if image.startswith("ghcr.io/"):
            githubOutput.write(f"ghcrStrippedDigest={multiArchDigest}\n")
        elif image.startswith("index.docker.io/"):
            githubOutput.write(f"dockerhubStrippedDigest={multiArchDigest}\n")
        elif image.startswith("public.ecr.aws/"):
            githubOutput.write(f"awsEcrStrippedDigest={multiArchDigest}\n")

    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("TAG")
    parser.add_argument("STRIPPED_DIGEST")
    parser.add_argument("DEBUGGABLE_DIGEST")
    parser.add_argument("IMAGES", nargs="+")
    args = parser.parse_args()

    failed = False
    for image in args.IMAGES:
        for t, digest in (
            (args.TAG, args.STRIPPED_DIGEST),
            (f"{args.TAG}-debuggable", args.DEBUGGABLE_DIGEST),
        ):
            if not mergeimage(image, t, digest):
                failed = True

    if failed:
        return 1
    return 0


if __name__ == "__main__":
    exit(main())
