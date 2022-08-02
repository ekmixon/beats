import argparse
from collections import OrderedDict
from functools import lru_cache
import os
import re
import requests

import yaml


def document_fields(output, section, sections, path):
    if "skipdocs" in section:
        return
    if "anchor" in section:
        output.write(f'[[exported-fields-{section["anchor"]}]]\n')

    if "prefix" in section:
        output.write(f'{section["prefix"]}\n')

    # Intermediate level titles
    if ("description" in section and "prefix" not in section and
            "anchor" not in section):
        output.write("[float]\n")

    if "description" in section:
        if "anchor" in section and section["name"] == "ECS":
            output.write(f'== {section["name"]} fields\n\n')
            output.write("""
This section defines Elastic Common Schema (ECS) fields—a common set of fields
to be used when storing event data in {es}.

This is an exhaustive list, and fields listed here are not necessarily used by {beatname_uc}.
The goal of ECS is to enable and encourage users of {es} to normalize their event data,
so that they can better analyze, visualize, and correlate the data represented in their events.

See the {ecs-ref}[ECS reference] for more information.
""")
        elif "anchor" in section:
            output.write(f'== {section["name"]} fields\n\n')
            output.write(f'{section["description"]}\n\n')
        else:
            output.write(f'=== {section["name"]}\n\n')
            output.write(f'{section["description"]}\n\n')

    if "fields" not in section or not section["fields"]:
        return

    output.write("\n")
    for field in section["fields"]:

        # Skip entries which do not define a name
        if "name" not in field:
            continue

        newpath = field["name"] if path == "" else f"{path}." + field["name"]
        if "type" in field and field["type"] == "group":
            document_fields(output, field, sections, newpath)
        else:
            document_field(output, field, newpath)


def document_field(output, field, field_path):

    if "field_path" not in field:
        field["field_path"] = field_path

    output.write(f'*`{field["field_path"]}`*::\n+\n--\n')

    if "deprecated" in field:
        output.write(f'\ndeprecated:[{field["deprecated"]}]\n\n')

    if "description" in field:
        output.write(f'{field["description"]}\n\n')
    if "type" in field:
        output.write(f'type: {field["type"]}\n\n')
    if "example" in field:
        output.write(f'example: {field["example"]}\n\n')
    if "format" in field:
        output.write(f'format: {field["format"]}\n\n')
    if "required" in field:
        output.write(f'required: {field["required"]}\n\n')
    if "path" in field:
        output.write(f'alias to: {field["path"]}\n\n')

    # For Apm-Server docs only
    # Assign an ECS badge for ECS fields
    if beat_title == "Apm-Server" and field_path in ecs_fields():
        output.write("{yes-icon} {ecs-ref}[ECS] field.\n\n")

    if "index" in field and not field["index"]:
        output.write(f"Field is not indexed.\n\n")

    if "enabled" in field and not field["enabled"]:
        output.write(f"Object is not enabled.\n\n")

    output.write("--\n\n")

    if "multi_fields" in field:
        for subfield in field["multi_fields"]:
            document_field(output, subfield, (f"{field_path}." + subfield["name"]))


@lru_cache(maxsize=None)
def ecs_fields():
    """
    Fetch flattened ECS fields based on ECS 1.6.0 spec
    The result of this function is cached
    """
    url = "https://raw.githubusercontent.com/elastic/ecs/v1.6.0/generated/ecs/ecs_flat.yml"
    resp = requests.get(url)
    if resp.status_code != 200:
        raise ValueError(resp.content)
    return yaml.load(resp.content, Loader=yaml.FullLoader)


def fields_to_asciidoc(input, output, beat):

    dict = {'beat': beat}

    output.write("""
////
This file is generated! See _meta/fields.yml and scripts/generate_fields_docs.py
////

[[exported-fields]]
= Exported fields

[partintro]

--
This document describes the fields that are exported by {beat}. They are
grouped in the following categories:

""".format(**dict))

    docs = yaml.load(input, Loader=yaml.FullLoader)

    # fields file is empty
    if docs is None:
        print("fields.yml file is empty. fields.asciidoc cannot be generated.")
        return

    # deduplicate fields, last one wins
    for section in docs:
        if not section.get("fields"):
            continue
        fields = OrderedDict()
        for field in section["fields"]:
            name = field["name"]
            if name in fields:
                assert (
                    field["type"] == fields[name]["type"]
                ), f'field "{name}" redefined with different type "{field["type"]}"'

                fields[name].update(field)
            else:
                fields[name] = field
        section["fields"] = list(fields.values())

    # Create sections from available fields
    sections = {v["key"]: v["title"] for v in docs}
    for section in sorted(docs, key=lambda field: field["key"]):
        if "anchor" not in section:
            section["anchor"] = section["key"]

        if "skipdocs" not in section:
            output.write(f'* <<exported-fields-{section["anchor"]}>>\n')
    output.write("\n--\n")

    # Sort alphabetically by key
    for section in sorted(docs, key=lambda field: field["key"]):
        section["name"] = section["title"]
        if "anchor" not in section:
            section["anchor"] = section["key"]
        document_fields(output, section, sections, "")


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Generates the documentation for a Beat.")
    parser.add_argument("fields", help="Path to fields.yml")
    parser.add_argument("beattitle", help="The beat title")
    parser.add_argument("es_beats",
                        help="The path to the general beats folder")
    parser.add_argument("--output_path", default="", dest="output_path",
                        help="Output path, if different from path")

    args = parser.parse_args()

    fields_yml = args.fields
    beat_title = args.beattitle.title()
    es_beats = args.es_beats

    # Read fields.yml
    with open(fields_yml, encoding='utf-8') as f:
        fields = f.read()

    output = open(os.path.join(args.output_path, "docs/fields.asciidoc"), 'w', encoding='utf-8')

    try:
        fields_to_asciidoc(fields, output, beat_title)
    finally:
        output.close()
