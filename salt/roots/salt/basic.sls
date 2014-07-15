base:
  pkgrepo.managed:
    - humanname: Deadsnakes PPA
    - name: ppa:fkrull/deadsnakes
    - dist: precise
    - file: /etc/apt/sources.list.d/deadsnakes.list
    - keyid: 1024R
    - keyserver: keyserver.ubuntu.com
    - require_in:
      - pkg: python3.4

python3.4:
  pkg.installed

packges:
  pkg.installed:
    - pkgs:
      - gfortran
      - git
      - htop
      - libatlas-base-dev
      - libatlas-dev
      - libblas-dev
      - liblapack-dev
      - mercurial
      - prover9
      - python-dev
      - python-numpy
      - python-pip
      - python-scipy
      - python-sklearn
      - python-yaml
      - python2.6
      - python3-numpy
      - python3-yaml
      - python3.2
      - python3.3

python-pip:
  pkg.installed

pip:
  pip.installed:
    - name: pip >= 1.4
    - require:
      - pkg: python-pip

nose:
  pip.installed:
    - require:
      - pkg: python-pip

tox:
  pip.installed:
    - require:
      - pkg: python-pip

python-coveralls:
  pip.installed:
    - require:
      - pkg: python-pip

nltk_data:
  cmd.run:
    - name: python -m nltk.downloader -d /usr/share/nltk_data all
    - cwd: /vagrant

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

# LADR-2009-11A:
#   archive:
#     - extracted
#     - name: /opt/
#     - source: http://www.cs.unm.edu/~mccune/prover9/download/LADR-2009-11A.tar.gz
#     - archive_format: tar
#     - tar_options: z
#     - source_hash: sha512=f26d3713eb2ba809fb3d55ce179e9d91555ab9166e075aa0843bafe57ce00f153cfed178b61993d4fd471655840e4f40775d75dac9fb5242a67e5d59c970dfc7
#     - if_missing: /opt/LADR-2009-11A

# make_prover9:
#   cmd.run:
#     - name: make all
#     - cwd: /opt/LADR-2009-11A

# /opt/prover9:
#   file.symlink:
#     - target: /opt/LADR-2009-11A

hunpos:
  archive:
    - extracted
    - name: /opt/
    - source: https://hunpos.googlecode.com/files/hunpos-1.0-linux.tgz
    - archive_format: tar
    - tar_options: z
    - source_hash: sha512=2b15136e5f5b8bb4cf5c38715cab3e810d60192e9404d15d329fb788b95b92c582ffe982892a7d2d470b061e6f1bea3fa051138dc820d19280234275cbd9ddeb
    - if_missing: /opt/hunpos-1.0-linux/
