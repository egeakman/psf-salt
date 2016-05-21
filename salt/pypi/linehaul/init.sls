linehaul:
  pkg.installed:
    - pkgs:
      - git
      - virtualenv
      - python3-dev
      - libffi-dev
      - libssl-dev

  user.present:
    - name: linehaul
    - home: /srv/linehaul/
    - createhome: True

  git.latest:
    - name: https://github.com/pypa/linehaul.git
    - target: /srv/linehaul/src
    - user: linehaul
    - require:
      - pkg: linehaul
      - user: linehaul

  virtualenv.managed:
    - name: /srv/linehaul/env/
    - user: linehaul
    - requirements: /srv/linehaul/src/requirements.txt
    - python: /usr/bin/python3
    - require:
      - git: linehaul
      - user: linehaul
      - pkg: linehaul

  service.running:
    - enable: True
    - watch:
      - file: /etc/systemd/system/linehaul.service


/etc/systemd/system/linehaul.service:
  - source: salt://pypi/linehaul/linehaul.service.jinja
  - template: jinja
  - user: root
  - group: root
  - mode: 640
  - show_diff: False


/srv/linehaul/etc/bigquery.key:
  file.managed:
    - contents_pillar: linehaul:key
    - user: linehaul
    - group: linehaul
    - mode: 640
    - makedirs: True
    - show_diff: False
    - require:
      - user: linehaul