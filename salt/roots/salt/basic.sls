base:
  pkgrepo.managed:
    - humanname: Deadsnakes PPA
    - name: ppa:fkrull/deadsnakes
    - dist: precise
    - file: /etc/apt/sources.list.d/deadsnakes.list
    - keyid: DB82666C
    - keyserver: keyserver.ubuntu.com
    - require_in:
      - pkg: python3.4

python3.4:
  pkg.installed

packges:
  pkg.installed:
    - pkgs:
      - git
      - htop
      - libatlas-base-dev
      - libatlas-dev
      - libblas-dev
      - liblapack-dev
      - mercurial
      - openjdk-7-jre-headless
      - prover9
      - python-dev
      - python-pip
      - python2.6
      - python2.6-dev
      - python3.2
      - python3.2-dev
      - python3.3
      - python3.3-dev
      - python3.4-dev

tox:
  pip.installed

coveralls:
  pip.installed

nose:
  pip.installed

{% for py in '3.4', '3.3', '3.2', '2.7', '2.6' %}
pip{{ py }}:
  cmd.run:
    - name: curl https://bootstrap.pypa.io/get-pip.py | python{{ py }} - -I

{% for pkg in 'numpy', 'scipy', 'scikit-learn' %}
{{pkg}}{{ py }}:
  cmd.run:
    - name: pip{{ py }} install --use-wheel --no-index --find-links=https://dl.dropboxusercontent.com/u/50040986/index/index.html {{pkg}}
{% endfor %}

{% endfor %}

nltk_data:
  cmd.run:
    - name: python -m nltk.downloader -d /usr/share/nltk_data all
    - cwd: /vagrant
    - onlyif: ls /vagrant

malt:
  archive:
    - extracted
    - name: /opt/
    - source: http://maltparser.org/dist/maltparser-1.8.tar.gz
    - archive_format: tar
    - tar_options: z
    - source_hash: sha512=e613c20ad7dfe06a7698e059d7eb18cd1120985afedb043e8e6991bae54136d7ac844e078483e5530e541e3f526e8f2eae4e61594b79671d94531dbfefbb17cc
    - if_missing: /opt/maltparser-1.8

/opt/maltparser-1.8/malt.jar:
  file.symlink:
    - target: /opt/maltparser-1.8/maltparser-1.8.jar

hunpos:
  archive:
    - extracted
    - name: /opt/
    - source: https://hunpos.googlecode.com/files/hunpos-1.0-linux.tgz
    - archive_format: tar
    - tar_options: z
    - source_hash: sha512=2b15136e5f5b8bb4cf5c38715cab3e810d60192e9404d15d329fb788b95b92c582ffe982892a7d2d470b061e6f1bea3fa051138dc820d19280234275cbd9ddeb
    - if_missing: /opt/hunpos-1.0-linux/

senna:
  archive:
    - extracted
    - name: /usr/share
    - source: http://ml.nec-labs.com/senna/senna-v2.0/senna-v2.0.tgz
    - archive_format: tar
    - tar_options: z
    - source_hash: sha512= a98cf218b9a059ac70b9ef36a28d6c9c68b76e95c2cd7facfb21bc8e5787a91f2c47022f3a36cbb8c5abf5e2962bc5db58effabf04fc69f9caa23be3827de92d
    - if_missing: /usr/share/senna-v2.0

/bin/megam:
  file.managed:
    - source: https://dl.dropboxusercontent.com/u/50040986/index/megam
    - user: root
    - group: root
    - mode: '0755'
    - source_hash: sha512=32999071f2365972022b78659d4135cd45897a15b4361d49b570876956b41d8f063b9bb351c18ac010b399edd9a616ccf2fe538e1d3e38eb5a763b6be6046466
