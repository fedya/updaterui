#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from distutils.version import LooseVersion
import re
import tempfile
import json


headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Cache-Control": "max-age=0",
}

def compare_versions(v1, v2):
    try:
        if LooseVersion(v1) < LooseVersion(v2):
            # outdated
            return "outdated"
        elif LooseVersion(v1) == LooseVersion(v2):
            # same
            return "up-to-date"
        else:
            # our newer
            return "our-newer"
    except Exception:
        pass

def get_latest_version(package):
    if package.startswith("python-"):
       package = package.split("-", 1)[1]
    url = f"https://pypi.python.org/pypi/{package}/json"
    response = requests.get(url)
    if response.ok:
        data = response.json()
        return data["info"]["version"]
    else:
        return "0"

def get_rosa_version(package):
    url = "https://abf.io/import/{package}/raw/rosa2023.1/{package}.spec".format(package=package)
    print(url)
    resp = requests.get(url, headers=headers)
    temp = tempfile.NamedTemporaryFile(prefix=package, suffix=".spec")
    if resp.status_code == 404:
        return "Package not found"
    if resp.status_code == 200:
        spec = resp.content
        try:
            spec_path = temp.name
            temp.write(spec)
            temp.seek(0)
            with open(spec_path, "r") as f:
                content = f.read()
                match = re.search(r"Version:\s+(.*)\n", content)
                if match:
                    return match.group(1)
        except:
            pass
        finally:
            temp.close()
    return "0"

with open("packages.txt") as f:
    packages = [line.strip() for line in f.readlines()]
results = []

for package in packages:
    rosa_version = get_rosa_version(package) # здесь нужно поставить функцию-заглушку для получения версии из Rosa
    upstream_version = get_latest_version(package)
    if upstream_version is None:
        continue
    status = compare_versions(rosa_version, upstream_version)
    result = {
        "package": package,
        "version_rosa": rosa_version,
        "version_upstream": upstream_version,
        "status": status,
        "upgrade": ""
    }
    results.append(result)

with open("output.json", "w") as f:
    json.dump(results, f, indent=4)


#a = get_rosa_version("python-backcall")
#b = get_latest_version("vim")
#compare_versions(a, b)
