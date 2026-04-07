import datetime as dt
import re
import xml.etree.ElementTree as ET

FIELD_TAGS = {
    "textfield",
    "textarea",
    "numberfield",
    "datefield",
    "emailfield",
    "phonefield",
    "selectfield",
    "checkfield",
    "radiogroup",
    "computed",
    "printvar",
}

FORMAT_TAGS = {
    "b", 
    "i", 
    "u", 
    "s",
    "h3",
    "n"
}

COLOR_TAGS = {
    "red",
    "green",
    "lightgreen",
    "blue",
    "lightblue",
    "yellow",
    "orange",
    "cyan",
    "magenta",
    "black",
    "white",
    "gray",
    "lightgray",
    "bg_red",
    "bg_green",
    "bg_yellow",
    "bg_blue",
    "bg_magenta",
    "bg_cyan",
    "bg_black",
    "bg_white",
    "bg_gray",
}


def parse_fxml(file_path: str, raw_values=None):
    tree = ET.parse(file_path)
    root = tree.getroot()

    if root.tag != "form":
        raise ValueError("Il file FXML deve avere <form> come elemento radice")

    form_attributes = root.attrib
    field_defs = _collect_field_definitions(root)
    form_data = _normalize_form_values(raw_values or {}, field_defs)
    variables = _evaluate_variables(root, form_data)
    context = _build_context(form_data, variables)
    variable_defs = parse_variables(root)
    conditionals = parse_conditionals(root)
    nodes = _parse_nodes(root, context)
    return form_attributes, nodes, variables, form_data, conditionals, variable_defs


def _parse_nodes(node, context):
    parsed = []

    for child in node:
        if child.tag == "script":
            continue

        if child.tag in {"variables", "var", "validate", "option"}:
            continue

        if child.tag == "section":
            parsed.append(
                {
                    "type": "section",
                    "title": child.get("title"),
                    "children": _parse_nodes(child, context),
                }
            )
            continue

        if child.tag == "row":
            parsed.append(
                {
                    "type": "row",
                    "children": _parse_nodes(child, context),
                }
            )
            continue

        if child.tag == "conditional":
            parsed.append(
                {
                    "type": "conditional",
                    "if": child.get("if", ""),
                    "children": _parse_nodes(child, context),
                }
            )
            continue

        if child.tag == "pagebreak":
            parsed.append({"type": "pagebreak"})
            continue

        if child.tag == "text":
            segments = _parse_text_segments(child, context)
            plain_text = "".join(segment["text"] for segment in segments)
            parsed.append(
                {
                    "type": "text",
                    "text": plain_text,
                    "segments": segments,
                }
            )
            continue

        if child.tag in FIELD_TAGS:
            parsed.append(_parse_field(child, context))

    return parsed


def _parse_field(node, context):
    field = {
        "type": node.tag,
        "name": node.get("name"),
        "label": node.get("label"),
        "required": node.get("required") == "true",
    }

    for attr in (
        "width",
        "maxlength",
        "placeholder",
        "min",
        "max",
        "step",
        "rows",
        "value",
        "default",
        "readonly",
    ):
        value = node.get(attr)
        if value is not None:
            field[attr] = value

    if node.tag in {"selectfield", "radiogroup"}:
        field["options"] = [
            {
                "value": opt.get("value", ""),
                "text": (opt.text or "").strip(),
            }
            for opt in node.findall("option")
        ]

    validations = []
    for validate in node.findall("validate"):
        validations.append(
            {
                "pattern": validate.get("pattern"),
                "message": validate.get("message"),
                "expr": validate.get("expr"),
            }
        )
    if validations:
        field["validations"] = validations

    name = field.get("name")
    if name:
        field["current_value"] = context.get(name)

    if node.tag == "printvar":
        field["value"] = context.get(name, "") if name else ""

    if node.tag == "computed":
        raw_value = field.get("value", "")
        field["resolved_value"] = _interpolate_value(raw_value, context)

    return field


def _collect_field_definitions(node, definitions=None):
    if definitions is None:
        definitions = {}

    for child in node:
        if child.tag in FIELD_TAGS and child.get("name"):
            definitions[child.get("name")] = {
                "type": child.tag,
                "step": child.get("step"),
            }
        _collect_field_definitions(child, definitions)

    return definitions


def _normalize_form_values(raw_values, field_definitions):
    normalized = {}

    for name, meta in field_definitions.items():
        raw_value = raw_values.get(name)
        normalized[name] = _convert_value(raw_value, meta["type"], meta.get("step"))

    return normalized


def _convert_value(value, field_type, step=None):
    if field_type == "checkfield":
        return _to_bool(value)

    if value is None or value == "":
        return None

    if field_type == "datefield":
        try:
            return dt.date.fromisoformat(value)
        except ValueError:
            return None

    if field_type == "numberfield":
        try:
            if step and "." in step:
                return float(value)
            return int(value)
        except ValueError:
            return None

    return value


def _to_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "on", "yes", "si"}


def _evaluate_variables(root, form_data):
    variables = {}
    variables_root = root.find("variables")
    if variables_root is None:
        return variables

    for var_node in variables_root.findall("var"):
        var_name = var_node.get("name")
        expression = var_node.get("expr", "")
        if not var_name:
            continue

        context = _build_context(form_data, variables)
        variables[var_name] = _safe_eval(expression, context)

    return variables


def _build_context(form_data, variables):
    context = {
        "today": dt.date.today(),
        "now": dt.datetime.now(),
    }
    context.update(form_data)
    context.update(variables)
    return context


def _evaluate_condition(expression, context):
    parsed_expression = _replace_dollar_refs(expression)
    result = _safe_eval(parsed_expression, context)
    return bool(result)


def _interpolate_value(text, context):
    if text is None:
        return ""

    placeholder = "__FXML_DOLLAR__"
    value = text.replace("$$", placeholder)

    def repl(match):
        key = match.group(1)
        resolved = context.get(key)
        return "" if resolved is None else str(resolved)

    value = re.sub(r"\$([A-Za-z_][A-Za-z0-9_]*)", repl, value)
    return value.replace(placeholder, "$")


def _parse_text_segments(node, context):
    segments = []

    def add_segment(raw_text, active_tags):
        if raw_text is None:
            return

        resolved = _interpolate_value(raw_text, context)
        if resolved == "":
            return

        classes = _tags_to_classes(active_tags)
        segments.append(
            {
                "text": resolved,
                "classes": classes,
            }
        )

    def walk(current_node, active_tags):
        add_segment(current_node.text, active_tags)

        for subnode in current_node:
            tag = subnode.tag
            next_active = active_tags
            if tag in FORMAT_TAGS or tag in COLOR_TAGS:
                next_active = [*active_tags, tag]

            walk(subnode, next_active)
            add_segment(subnode.tail, active_tags)

    walk(node, [])
    return segments


def _tags_to_classes(tags):
    classes = []

    for tag in tags:
        if tag in FORMAT_TAGS:
            classes.append(f"fmt-{tag}")
        elif tag in COLOR_TAGS:
            classes.append(f"clr-{tag}")

    return classes


def _replace_dollar_refs(expression):
    return re.sub(r"\$([A-Za-z_][A-Za-z0-9_]*)", r"\1", expression or "")


def _safe_eval(expression, context):
    try:
        return eval(expression, {"__builtins__": {}}, context)
    except Exception:
        return None


def parse_variables(root):
    variables_root = root.find("variables")
    if variables_root is None:
        return []

    definitions = []
    for var_node in variables_root.findall("var"):
        name = var_node.get("name")
        expr = var_node.get("expr", "")
        if name:
            definitions.append({"name": name, "expr": expr})
    return definitions


def parse_conditionals(root):
    parsed = []
    _walk_conditionals(root, parsed)
    return parsed


def _walk_conditionals(node, parsed):
    for child in node:
        if child.tag == "conditional":
            fields = []
            _collect_conditional_fields(child, fields)
            parsed.append(
                {
                    "if": child.get("if", ""),
                    "fields": fields,
                }
            )
        _walk_conditionals(child, parsed)


def _collect_conditional_fields(node, fields):
    for child in node:
        if child.tag in FIELD_TAGS and child.get("name"):
            fields.append(child.get("name"))
        _collect_conditional_fields(child, fields)


def extract_runtime_outputs(nodes):
    outputs = {
        "printvars": {},
        "computed": {},
    }
    _walk_runtime_nodes(nodes, outputs)
    return outputs


def _walk_runtime_nodes(nodes, outputs):
    for node in nodes:
        node_type = node.get("type")
        if node_type == "printvar" and node.get("name"):
            outputs["printvars"][node["name"]] = node.get("value", "")
        if node_type == "computed" and node.get("name"):
            outputs["computed"][node["name"]] = node.get("resolved_value", "")

        children = node.get("children")
        if isinstance(children, list):
            _walk_runtime_nodes(children, outputs)