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

api_key = os.environ.get('API_KEY')
github_headers = {'User-Agent': 'Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.2171.95 Safari/537.36',
                  'Authorization': f'token {api_key}'}


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


def has_latin_letters(s):
    pattern = re.compile(r'[a-zA-Z]')
    return bool(pattern.search(s))

def gh_check(package, url):
    split_url = url.split("/")[:-1]
    apibase = 'https://api.github.com/repos' + '/' + split_url[3] + '/' + split_url[4]
    tag_url = apibase + "/tags"
    release_url = apibase + "/releases/latest"
    gh_versions = []

    response_rel = requests.get(release_url, headers=github_headers)
    print(release_url)
    if response_rel.ok:
       tag_name = response_rel.json()['tag_name']
       if has_latin_letters(tag_name):
           gh_versions.append("0")
       else:
           gh_versions.append(tag_name)

    response_tag = requests.get(tag_url, headers=github_headers)
    print(tag_url)
    if response_tag.ok:
       data = response_tag.json()
       project_name = (data[0]['name'])
       versions = sorted(data, key=lambda x: x['name'], reverse=True)
       tag_version = versions[0]
       print(tag_version)
       clean_tag = tag_version["name"].strip("v")
       if has_latin_letters(clean_tag):
           gh_versions.append("0")
       else:
           gh_versions.append(clean_tag)

    if len(gh_versions) > 1:
       if compare_versions(gh_versions[0], gh_versions[1]) == "our-newer":
           print("version obtained from TAG [{}] is newer than in RELEASE [{}] json".format(gh_versions[0], gh_versions[1]))
           return gh_versions[0]
       if compare_versions(gh_versions[0], gh_versions[1]) == "outdated":
           print("version obtained from RELEASE [{}] is newer than in TAG [{}] json".format(gh_versions[1], gh_versions[0]))
           return gh_versions[1]
    if len(gh_versions) == 1:
       return gh_versions[0]

def get_latest_version(package, url_base):
    if package.startswith("python-"):
       package = package.split("-", 1)[1]
       return check_python_module(package)
    if "github" in url_base:
       print("checking github")
       return gh_check(package, url_base)
    return "0"


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
            nvs = []
            for (filename, num, flags) in rpm_spec.sources:
                if num == 0 and flags == 1:
                    # path
                    # http://mirrors.n-ix.net/mariadb/mariadb-10.3.9/source/
                    source_link = '/'.join(filename.split("/")[:-1])
                    nvs.append(source_link)
                    nvs.append(filename)
                    return version, source_link
        except:
            return "broken"
        finally:
            os.remove(spec_file)
    return "0"


def update_single(package):
    with open('output.json', 'r') as f:
        data = json.load(f)
    found = False
    rosa_version, url_base = get_rosa_version(package) # здесь нужно поставить функцию-заглушку для получения версии из Rosa
    upstream_version = get_latest_version(package, url_base)
    status = compare_versions(rosa_version, upstream_version)
    for row in data:
        if row['package'] == package:
            row['version_rosa'] = rosa_version
            row['version_upstream'] = upstream_version
            row['status'] = status
            row['url'] = url_base
            found = True
            break

    if not found:
        new_row = {
            'package': package,
            'version_rosa': rosa_version,
            'version_upstream': upstream_version,
            'url': url_base,
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
        rosa_version, url_base = get_rosa_version(package)
        upstream_version = get_latest_version(package, url_base)
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
