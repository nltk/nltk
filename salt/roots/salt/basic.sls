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
      # - python-dev
      # - python-numpy
      # - python-scipy
      # - python-sklearn
      # - python-yaml

python-pip:
  pkg.installed

# pip:
#   pip.installed:
#     - name: pip >= 1.4
#     - require:
#       - pkg: python-pip

nose:
  pip.installed:
    - require:
      - pkg: python-pip

tox:
  pip.installed:
    - require:
      - pkg: python-pip

coveralls:
  pip.installed:
    - require:
      - pkg: python-pip

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
