import argparse
import os

from app.schemas.core.configuration import ConfigFile

parser = argparse.ArgumentParser()
parser.add_argument("--output", type=str, default="docs-legacy/configuration.md")


def get_documentation_data(title: str, data: list, properties: dict, defs: dict, header: str = "", level: int = 1):
    # attribute, type, description, required, default, values, examples
    table = list()
    for property in sorted(properties):
        type, values, description, required, default, examples = "", "", "", "", "", ""

        description = properties[property].get("description", "")
        required = properties[property].get("required", "")
        default = properties[property].get("default", "")
        examples = properties[property].get("examples", [""])[0]

        if "anyOf" in properties[property]:
            properties[property].update(properties[property]["anyOf"][0])

        if "$ref" in properties[property]:
            ref_key = properties[property]["$ref"].split("/")[-1]
            ref = defs[ref_key]
            type = ref["type"]
            values = ref.get("enum", [])

            # neested object section, get the data from the nested section
            if "properties" in ref:
                data = get_documentation_data(
                    title=ref_key,
                    data=data,
                    properties=ref["properties"],
                    defs=defs,
                    header=ref.get("description"),
                    level=level + 1,
                )
                description += f" For details of configuration, see the [{ref_key} section](#{ref_key.lower().replace(" ", "-")})."

        else:
            type = properties[property].get("type", "")
            values = properties[property].get("enum", [])

        if type == "array" and "$ref" in properties[property]["items"]:
            ref_key = properties[property]["items"]["$ref"].split("/")[-1]
            ref = defs[ref_key]

            # neested array section, get the data from the nested section
            if "properties" in ref:
                data = get_documentation_data(
                    title=ref_key,
                    data=data,
                    properties=ref["properties"],
                    defs=defs,
                    header=ref.get("description"),
                    level=level + 1,
                )
                description += f" For details of configuration, see the [{ref_key} section](#{ref_key.lower().replace(" ", "-")})."
            else:
                values = ref.get("enum", [])

        table.append([property, type, description, required, default, values, examples])

    data.append({"title": title, "table": table, "level": level, "header": header})

    return data


def convert_to_markdown(data: list):
    markdown = ""
    for item in reversed(data):
        markdown += f"{"#" * item["level"]} {item["title"]}\n"
        if item["header"]:
            markdown += f"{item["header"]}\n<br>\n\n"

        if len(item["table"]) > 0:
            markdown += "| Attribute | Type | Description | Required | Default | Values | Examples |\n"
            markdown += "| --- | --- | --- | --- | --- | --- | --- |\n"
            for row in item["table"]:
                if len(row[5]) > 10:
                    row[5] = "• " + "<br/>• ".join(row[5][:8]) + "<br/>• ..."
                elif len(row[5]) > 0:
                    row[5] = "• " + "<br/>• ".join(row[5])
                else:
                    row[5] = ""

                markdown += "| " + " | ".join(str(cell) for cell in row) + " |\n"

        elif item["header"] == "":
            markdown += "No settings."

        markdown += "\n<br>\n\n"

    return markdown


if __name__ == "__main__":
    args = parser.parse_args()
    assert args.output.endswith(".md"), "Output file must end with .md"
    assert os.path.exists(os.path.dirname(args.output)), "Output directory does not exist"

    schema = ConfigFile.model_json_schema()
    properties = schema["properties"]
    defs = schema["$defs"]

    data = get_documentation_data(title="All settings", data=[], properties=properties, header=schema.get("description", ""), defs=defs)
    markdown = convert_to_markdown(data=data)

    with open(file=args.output, mode="w") as f:
        f.write(markdown)
