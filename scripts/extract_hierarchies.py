#!/usr/bin/env python3
"""Extract class hierarchies from Mapped and Willow ontologies."""

import json
from collections import defaultdict
from pathlib import Path


def load_ontology(filepath):
    """Load ontology JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)


def build_hierarchy(interfaces, root_ids, id_prefix):
    """Build class hierarchy starting from root classes.

    Args:
        interfaces: List of interface definitions
        root_ids: List of root class IDs to start from
        id_prefix: Prefix to strip from IDs for cleaner names

    Returns:
        Dict mapping class names to their children
    """
    # Build parent -> children mapping
    children_map = defaultdict(list)
    id_to_name = {}

    for iface in interfaces:
        iface_id = iface.get('@id', '')
        extends = iface.get('extends', [])

        # Get display name
        display_name = iface.get('displayName', '')
        if isinstance(display_name, dict):
            display_name = display_name.get('en', '')

        # Use displayName or extract from ID
        if not display_name:
            display_name = iface_id.split(':')[-1].replace(';1', '')

        id_to_name[iface_id] = display_name

        # Map parents to this child
        if isinstance(extends, list):
            for parent_id in extends:
                children_map[parent_id].append(iface_id)
        elif extends:
            children_map[extends].append(iface_id)

    return children_map, id_to_name


def get_descendants(class_id, children_map, id_to_name, visited=None):
    """Recursively get all descendants of a class.

    Returns a nested dict structure.
    """
    if visited is None:
        visited = set()

    if class_id in visited:
        return None
    visited.add(class_id)

    children = children_map.get(class_id, [])
    result = {}

    for child_id in sorted(children, key=lambda x: id_to_name.get(x, x)):
        child_name = id_to_name.get(child_id, child_id)
        child_descendants = get_descendants(child_id, children_map, id_to_name, visited.copy())
        result[child_name] = {
            'id': child_id,
            'children': child_descendants if child_descendants else {}
        }

    return result


def format_hierarchy(hierarchy, indent=0):
    """Format hierarchy as indented text."""
    lines = []
    for name, data in sorted(hierarchy.items()):
        lines.append("  " * indent + f"- {name}")
        if data.get('children'):
            lines.extend(format_hierarchy(data['children'], indent + 1).split('\n'))
    return '\n'.join(lines)


def count_classes(hierarchy):
    """Count total classes in hierarchy."""
    count = 0
    for name, data in hierarchy.items():
        count += 1
        if data.get('children'):
            count += count_classes(data['children'])
    return count


def main():
    base_path = Path(__file__).parent.parent / 'data' / 'ontologies'

    # ========== MAPPED ONTOLOGY ==========
    print("Processing Mapped ontology...")
    mapped_data = load_ontology(base_path / 'mapped.json')
    mapped_children, mapped_names = build_hierarchy(mapped_data, [], 'dtmi:mapped:core:')

    # Find root classes for Mapped
    # Note: Mapped uses Brick schema for Collection
    mapped_roots = {
        'Thing': 'dtmi:mapped:core:Thing;1',
        'Collection': 'dtmi:org:brickschema:schema:Brick:Collection;1',
        'Place': 'dtmi:mapped:core:Place;1'
    }

    mapped_hierarchies = {}
    for root_name, root_id in mapped_roots.items():
        hierarchy = get_descendants(root_id, mapped_children, mapped_names)
        mapped_hierarchies[root_name] = {
            'id': root_id,
            'children': hierarchy if hierarchy else {}
        }

    # Write Mapped hierarchy
    with open(base_path / 'mapped_hierarchy.txt', 'w') as f:
        f.write("MAPPED ONTOLOGY CLASS HIERARCHY\n")
        f.write("=" * 50 + "\n\n")

        for root_name, root_data in mapped_hierarchies.items():
            count = count_classes(root_data.get('children', {}))
            f.write(f"\n{root_name} ({root_data['id']})\n")
            f.write(f"Total descendants: {count}\n")
            f.write("-" * 40 + "\n")
            if root_data.get('children'):
                f.write(format_hierarchy(root_data['children']))
            f.write("\n")

    print(f"Wrote Mapped hierarchy to {base_path / 'mapped_hierarchy.txt'}")

    # ========== WILLOW ONTOLOGY ==========
    print("\nProcessing Willow ontology...")
    willow_data = load_ontology(base_path / 'willow.jsonld')
    willow_children, willow_names = build_hierarchy(willow_data, [], 'dtmi:com:willowinc:')

    # Find root classes for Willow
    willow_roots = {
        'Asset': 'dtmi:com:willowinc:Asset;1',
        'Collection': 'dtmi:com:willowinc:Collection;1',
        'Space': 'dtmi:com:willowinc:Space;1'
    }

    willow_hierarchies = {}
    for root_name, root_id in willow_roots.items():
        hierarchy = get_descendants(root_id, willow_children, willow_names)
        willow_hierarchies[root_name] = {
            'id': root_id,
            'children': hierarchy if hierarchy else {}
        }

    # Write Willow hierarchy
    with open(base_path / 'willow_hierarchy.txt', 'w') as f:
        f.write("WILLOW ONTOLOGY CLASS HIERARCHY\n")
        f.write("=" * 50 + "\n\n")

        for root_name, root_data in willow_hierarchies.items():
            count = count_classes(root_data.get('children', {}))
            f.write(f"\n{root_name} ({root_data['id']})\n")
            f.write(f"Total descendants: {count}\n")
            f.write("-" * 40 + "\n")
            if root_data.get('children'):
                f.write(format_hierarchy(root_data['children']))
            f.write("\n")

    print(f"Wrote Willow hierarchy to {base_path / 'willow_hierarchy.txt'}")

    # Print summaries
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)

    print("\nMapped Ontology:")
    for root_name, root_data in mapped_hierarchies.items():
        count = count_classes(root_data.get('children', {}))
        print(f"  {root_name}: {count} descendants")

    print("\nWillow Ontology:")
    for root_name, root_data in willow_hierarchies.items():
        count = count_classes(root_data.get('children', {}))
        print(f"  {root_name}: {count} descendants")


if __name__ == '__main__':
    main()
