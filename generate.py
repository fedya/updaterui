#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from packaging.version import Version
import re
import tempfile
import json
import rpm
import os
import argparse
import sqlite3


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


def create_database():
    conn = sqlite3.connect('mydatabase.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS mytable
                      (package text PRIMARY KEY, version_rosa text, version_upstream text,
                       url text, status text, upgrade text)''')

    conn.commit()
    conn.close()


def add_or_update_data(result):
    create_database()
    conn = sqlite3.connect('mydatabase.db')
    cursor = conn.cursor()
    query = 'SELECT COUNT(*) FROM mytable WHERE package = ?'
    values = (result['package'], )
    cursor.execute(query, values)
    count = cursor.fetchone()[0]

    if count > 0:
        query = '''UPDATE mytable
                   SET version_rosa = ?, version_upstream = ?, url = ?, status = ?, upgrade = ?
                   WHERE package = ?'''
        values = (result['version_rosa'], result['version_upstream'], result['url'],
                  result['status'], result['upgrade'], result['package'])
        cursor.execute(query, values)
        print("record updated in db")
    else:
        query = '''INSERT INTO mytable (package, version_rosa, version_upstream, url, status, upgrade)
                   VALUES (?, ?, ?, ?, ?, ?)'''
        values = (result['package'], result['version_rosa'], result['version_upstream'],
                  result['url'], result['status'], result['upgrade'])
        cursor.execute(query, values)
        print("added to sqlite db")

    conn.commit()
    conn.close()


def repology(package):
    url = f'https://repology.org/api/v1/project/{package}'
    try:
        response = requests.get(url, timeout=20)
        data = response.json()
        print('im in repology')
        if not data:
            return "0", "0"

        for package_info in data:
            if is_valid_package_info(package_info):
                return package_info['version'], package_info['repo']

        return "0", "0"
    except requests.exceptions.Timeout:
        print('Request to repology timed out')
        return "0", "0"

def is_valid_package_info(repology):
    required_keys = ('status', 'repo')
    valid_statuses = ('newest', 'untrusted', 'unique')

    if all(key in repology for key in required_keys):
        if repology['status'] in valid_statuses:
            return True

    return False


def qt_check(upstream_url):
    # avoid nazi sanction
    if 'qt.io' in upstream_url:
        upstream_url = upstream_url.replace("https://download.qt.io/", "https://qt-mirror.dannhauer.de/")
    elif 'qt-project' in upstream_url:
        upstream_url = upstream_url.replace("http://download.qt-project.org/", "https://qt-mirror.dannhauer.de/")
    print(upstream_url)
    split_url = upstream_url.split("/")[:6]
    project_url = '/'.join(split_url[:6])
    req = requests.get(project_url, headers=headers, allow_redirects=True)
    version_list = []
    true_version_list = []
    if req.status_code == 404:
        print('requested url [{}] not found'.format(upstream_url))
        return
    if req.status_code == 200:
        try:
            first_url = re.finditer('href=[\'"]?([\d.]*\d+)', req.content.decode('utf-8'))
            for match in first_url:
                version_list.append(match[1])
            upstream_max_version = max([[int(j) for j in i.split(".")] for i in version_list])
            upstream_version = ".".join([str(i) for i in upstream_max_version])
            print(upstream_version)
            new_url = project_url + '/' + upstream_version
            req2 = requests.get(new_url, headers=headers, allow_redirects=True)
            if req2.status_code == 404:
                print('requested url [{}] not found'.format(new_url))
                return
            return upstream_version
        except:
            return


def check_python_module(package):
    url = "https://pypi.python.org/pypi/{}/json".format(package)
    response = requests.get(url)
    if response.ok:
        data = response.json()
        if data:
           print(data["info"]["version"])
           return data["info"]["version"]
    else:
        package = "py" + package
        url = "https://pypi.python.org/pypi/{}/json".format(package)
        response = requests.get(url)
        if response.ok:
            data = response.json()
            if data:
               print(data["info"]["version"])
               return data["info"]["version"]
        else:
            return 0
    return "0"


def compare_versions(v1, v2):
    try:
        if Version(v1) < Version(v2):
            return "outdated"
        elif Version(v1) == Version(v2):
            return "up-to-date"
        else:
            return "our-newer"
    except Exception:
        return "something wrong here"


def has_latin_letters(s):
    pattern = re.compile(r'[a-zA-Z]')
    return bool(pattern.search(s))

def gh_check(package, url):
    split_url = url.split("/")[:-1]
    apibase = 'https://api.github.com/repos' + '/' + split_url[3] + '/' + split_url[4]
    tag_url = apibase + "/tags"
    release_url = apibase + "/releases/latest"
    print(release_url)
    gh_versions = []
    response_rel = requests.get(release_url, headers=github_headers)
    print(response_rel)
    if response_rel.ok:
       tag_name = re.sub(r"[^0-9\.]", "", response_rel.json()['tag_name'])
       if len(tag_name) > 0 and has_latin_letters(tag_name):
           print("tag_name")
           gh_versions.append("0")
       elif tag_name:
           gh_versions.append(tag_name)
    else:
        gh_versions.append("0")

    response_tag = requests.get(tag_url, headers=github_headers)
    print(tag_url)
    if response_tag.ok:
       data = response_tag.json()
       if len(data) > 0:
          project_name = (data[0]['name'])
          versions = sorted(data, key=lambda x: x['name'], reverse=True)
          tag_version = versions[0]
          clean_tag = re.sub(r"[^0-9\.]", "", tag_version["name"])
          if clean_tag and has_latin_letters(clean_tag):
              gh_versions.append("0")
          elif clean_tag:
              gh_versions.append(clean_tag)
    else:
        gh_versions.append("0")

    if len(gh_versions) > 1:
       if compare_versions(gh_versions[0], gh_versions[1]) == "our-newer":
           print("version obtained from TAG [{}] is newer than in RELEASE [{}] json".format(gh_versions[0], gh_versions[1]))
           return gh_versions[0]
       if compare_versions(gh_versions[0], gh_versions[1]) == "outdated":
           print("version obtained from RELEASE [{}] is newer than in TAG [{}] json".format(gh_versions[1], gh_versions[0]))
           return gh_versions[1]
       if compare_versions(gh_versions[0], gh_versions[1]) == "up-to-date":
           print("version obtained from RELEASE [{}] is SAME as in TAG [{}] json".format(gh_versions[1], gh_versions[0]))
           return gh_versions[0]
    if len(gh_versions) == 1:
       return gh_versions[0]
    return "0"

def get_latest_version(package, url_base):
    if package.startswith("python-"):
        package = package.split("-", 1)[1]
        return check_python_module(package)
    elif "github" in url_base:
        print("checking github")
        try:
            return gh_check(package, url_base)
        except Exception:
            return "0"
    elif 'qt.io' in url_base or 'qt-project' in url_base:
        return qt_check(url_base)
    else:
        upstream_version, repo = repology(package)
        return upstream_version
    return "0"


def get_rosa_version(package):
    url = "https://abf.io/import/{package}/raw/rosa2023.1/{package}.spec".format(package=package)
    print(url)
    resp = requests.get(url, headers=headers)
    temp = tempfile.NamedTemporaryFile(prefix=package, suffix=".spec")
    version = "0"
    source_link = "empty"
    if resp.status_code == 404:
        print("Package not found in git repo")
        return version, source_link
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
                    if source_link:
                       nvs.append(source_link)
                       nvs.append(filename)
                       return version, source_link
        except:
            return version, source_link
        finally:
            os.remove(spec_file)
    return version, source_link


def update_single(package):
    found = False
    rosa_version = "0"
    upstream_version = "0"
    status = "0"
    rosa_version, url_base = get_rosa_version(package)
    upstream_version = get_latest_version(package, url_base)
    status = compare_versions(rosa_version, upstream_version)
    data = {
        'package': package,
        'version_rosa': rosa_version,
        'version_upstream': upstream_version,
        'url': url_base,
        'status': status,
        'upgrade': ''
    }
    print(data)
    add_or_update_data(data)


def generate_data():
    with open("packages.txt") as f:
        packages = [line.strip() for line in f.readlines()]
    rosa_version = "0"
    upstream_version = "0"
    status = "0"
    for package in packages:
        print(package)
        rosa_version, url_base = get_rosa_version(package)
        upstream_version = get_latest_version(package, url_base)
        # problem
        status = compare_versions(rosa_version, upstream_version)
        result = {
            "package": package,
            "version_rosa": rosa_version,
            "version_upstream": upstream_version,
            "url": url_base,
            "status": status,
            "upgrade": ""
        }
        print(result)
        add_or_update_data(result)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--generate-all', action='store_true', help='Generate JSON file for all packages')
    parser.add_argument('--generate-single', metavar='PACKAGE', help='Update a single package in the JSON file')
    args = parser.parse_args()

    if args.generate_all:
        generate_data()
    if args.generate_single:
        update_single(args.generate_single)

if __name__ == '__main__':
    main()


#a = get_rosa_version("python-backcall")
#b = get_latest_version("vim")
#compare_versions(a, b)
