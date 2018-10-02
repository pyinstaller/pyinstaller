{% macro print_issue_numbers(issues) %}
{% for issue in issues if issue.startswith('#') %}
{% if loop.first %} ({% endif %}
:issue:`{{ issue }}`{% if not(loop.last) %}, {% endif %}
{% if loop.last %}){% endif %}
{% endfor %}
{% endmacro %}

{% for section, _ in sections.items() %}
{% set underline = underlines[0] %}{% if section %}{{section}}
{{ underline * section|length }}{% set underline = underlines[1] %}

{% endif -%}

{% if sections[section] %}
{% for category, val in definitions.items() if category in sections[section]%}
{{ definitions[category]['name'] }}
{{ underline * definitions[category]['name']|length }}

{% if definitions[category]['showcontent'] %}
{% for text, values in sections[section][category]|dictsort %}
* {{ text }}{{ print_issue_numbers(values|list) }}{# #}

{% endfor %}

{% else %}
* {{ sections[section][category]['']|join(', ') }}

{% endif %}
{% if sections[section][category]|length == 0 %}
No significant changes.

{% else %}
{% endif %}

{% endfor %}
{% else %}
No significant changes.


{% endif %}
{% endfor %}
