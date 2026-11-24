{% macro line_amount(units, unit_price, discount) %}
    ({{ units }} * {{ unit_price }} - {{ discount }})
{% endmacro %}
