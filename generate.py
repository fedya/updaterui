#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from distutils.version import LooseVersion
import re
import tempfile
import json
import rpm
import os
import argparse


headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Cache-Control": "max-age=0",
}


def check_python_module(package):
    url = "https://pypi.python.org/pypi/{}/json".format(package)
    response = requests.get(url)
    if response.ok:
        data = response.json()
        print(data["info"]["version"])
        return data["info"]["version"]
    else:
        package = "py" + package
        url = "https://pypi.python.org/pypi/{}/json".format(package)
        response = requests.get(url)
        if response.ok:
            data = response.json()
            print(data["info"]["version"])
            return data["info"]["version"]
        else:
            return 0
    return "0"


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
        return "something wrong here"
        pass


def get_latest_version(package):
    if package.startswith("python-"):
       package = package.split("-", 1)[1]
       return check_python_module(package)


def get_rosa_version(package):
    url = "https://abf.io/import/{package}/raw/rosa2023.1/{package}.spec".format(package=package)
    resp = requests.get(url, headers=headers)
    temp = tempfile.NamedTemporaryFile(prefix=package, suffix=".spec")
    if resp.status_code == 404:
        return "Package not found"
    if resp.status_code == 200:
        spec = resp.content
        try:
            spec_text = requests.get(url).text
            spec_file = f"/tmp/{package}.spec"
            with open(spec_file, "w") as f:
                f.write(spec_text)
            ts = rpm.TransactionSet()
            rpm_spec = ts.parseSpec(spec_file)
            name = rpm.expandMacro("%{name}")
            version = rpm.expandMacro("%{version}")
            print("checking ROSA git repo: {}: {}".format(package, version))
            return version
        except:
            return "broken"
        finally:
            os.remove(spec_file)
    return "0"


def update_single(package):
    with open('output.json', 'r') as f:
        data = json.load(f)
    found = False
    rosa_version = get_rosa_version(package) # здесь нужно поставить функцию-заглушку для получения версии из Rosa
    upstream_version = get_latest_version(package)
    for row in data:
        if row['package'] == package:
            row['version_rosa'] = rosa_version
            row['version_upstream'] = upstream_version
            status = compare_versions(rosa_version, upstream_version)
            row['status'] = status
            found = True
            break

    if not found:
        new_row = {
            'package': package,
            'version_rosa': get_rosa_version(package),
            'version_upstream': get_latest_version(package),
            'status': '',
            'upgrade': ''
        }
        data.append(new_row)

    with open('output.json', 'w') as f:
        json.dump(data, f, indent=4)


def generate_json():
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--generate-all', action='store_true', help='Generate JSON file for all packages')
    parser.add_argument('--generate-single', metavar='PACKAGE', help='Update a single package in the JSON file')
    args = parser.parse_args()

    if args.generate_all:
        generate_json()
    if args.generate_single:
        update_single(args.generate_single)

if __name__ == '__main__':
    main()


#a = get_rosa_version("python-backcall")
#b = get_latest_version("vim")
#compare_versions(a, b)
