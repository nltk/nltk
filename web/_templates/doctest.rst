{% for item in range(17 + module_name|length) -%}#{%- endfor %}
Sample usage for {{ module_name }}
{% for item in range(17 + module_name|length) -%}#{%- endfor %}

.. include:: ../../nltk/test/{{ module_name }}.doctest
