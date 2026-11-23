import urllib.request
import json
import os


def alpinePHPPackageSuffix(alpineVer: str, phpVer: str):
    # Since alpine 3.15, php packages have stable suffix
    # Change the map if this chanes in the future
    match phpVer:
        case "8.5":
            return "85"
        case "8.4":
            return "84"
        case "8.3":
            return "83"
        case "8.2":
            return "82"
        case "8.1":
            return "81"
        case "8.0":
            return "8"
        case "7.4":
            return "7"
        case _:
            raise ValueError(f"Unsupported alpine-php version: {alpineVer}-{phpVer}")


def getHEADRev(repo: str, ref: str) -> str:
    url = f"https://api.github.com/repos/{repo}/commits/{ref}"
    with urllib.request.urlopen(
        urllib.request.Request(
            url,
            headers={
                **(
                    {
                        "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
                    }
                    if os.environ.get("GITHUB_TOKEN")
                    else {}
                ),
                "Accept": "application/json",
                "User-Agent": "php-dockerfile/1.0",
            },
        )
    ) as response:
        data = json.loads(response.read().decode())
        return data["sha"]
