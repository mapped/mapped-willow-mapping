#!/usr/bin/env python3
"""Build a tree showing Willow hierarchy with mappings and suggestions."""

import json
import re
from pathlib import Path
from collections import defaultdict


def load_json(filepath):
    with open(filepath, 'r') as f:
        return json.load(f)


def get_display_name(iface):
    dn = iface.get('displayName', '')
    if isinstance(dn, dict):
        return dn.get('en', '')
    return dn


def normalize_name(name):
    return re.sub(r'[\s_-]', '', name).lower()


def build_ontology_graph(interfaces):
    """Build parent->children and child->parents maps."""
    children_map = defaultdict(list)
    parents_map = defaultdict(list)
    id_to_info = {}

    for iface in interfaces:
        iface_id = iface.get('@id', '')
        extends = iface.get('extends', [])
        display_name = get_display_name(iface)

        if not display_name:
            display_name = iface_id.split(':')[-1].replace(';1', '')

        id_to_info[iface_id] = {
            'id': iface_id,
            'name': display_name,
            'normalized': normalize_name(display_name)
        }

        if isinstance(extends, list):
            for parent_id in extends:
                children_map[parent_id].append(iface_id)
                parents_map[iface_id].append(parent_id)
        elif extends:
            children_map[extends].append(iface_id)
            parents_map[iface_id].append(extends)

    return children_map, parents_map, id_to_info


def get_ancestors(class_id, parents_map, visited=None):
    """Get all ancestors of a class."""
    if visited is None:
        visited = set()
    if class_id in visited:
        return set()
    visited.add(class_id)

    ancestors = set()
    for parent_id in parents_map.get(class_id, []):
        ancestors.add(parent_id)
        ancestors.update(get_ancestors(parent_id, parents_map, visited))
    return ancestors


def get_descendants(class_id, children_map, visited=None):
    """Get all descendants of a class."""
    if visited is None:
        visited = set()
    if class_id in visited:
        return set()
    visited.add(class_id)

    descendants = set()
    for child_id in children_map.get(class_id, []):
        descendants.add(child_id)
        descendants.update(get_descendants(child_id, children_map, visited))
    return descendants


def find_mapping_by_hierarchy(willow_id, willow_info, willow_parents,
                               existing_mappings, mapped_children, mapped_info):
    """Try to find a mapping using hierarchy relationships."""
    willow_name = willow_info.get(willow_id, {}).get('name', '')
    willow_normalized = normalize_name(willow_name)

    # Get Willow ancestors that have mappings
    ancestors = get_ancestors(willow_id, willow_parents)
    mapped_ancestors = [(a, existing_mappings[a]) for a in ancestors if a in existing_mappings]

    if not mapped_ancestors:
        return None, None

    # For each mapped ancestor, look for children in Mapped that match our name
    for willow_ancestor, mapped_target in mapped_ancestors:
        # Get descendants of the mapped target
        mapped_descendants = get_descendants(mapped_target, mapped_children)
        mapped_descendants.add(mapped_target)

        # Check if any descendant matches our name
        for mapped_id in mapped_descendants:
            mapped_name = mapped_info.get(mapped_id, {}).get('name', '')
            if normalize_name(mapped_name) == willow_normalized:
                return mapped_id, f"via parent {willow_info.get(willow_ancestor, {}).get('name', '')}"

    # If no exact match, suggest parent's mapping as fallback
    closest_ancestor = mapped_ancestors[0]
    return None, f"parent mapped to {mapped_info.get(closest_ancestor[1], {}).get('name', '')}"


def print_tree(class_id, willow_children, willow_info, existing_mappings,
               mapped_info, mapped_children, indent=0, visited=None, output_lines=None):
    """Recursively print the hierarchy tree."""
    if visited is None:
        visited = set()
    if output_lines is None:
        output_lines = []

    if class_id in visited:
        return output_lines
    visited.add(class_id)

    info = willow_info.get(class_id, {})
    name = info.get('name', class_id)

    # Check if mapped
    mapping = existing_mappings.get(class_id)
    if mapping:
        mapped_name = mapped_info.get(mapping, {}).get('name', mapping)
        line = f"{'  ' * indent}{name} -> {mapped_name}"
    else:
        line = f"{'  ' * indent}{name} -> [UNMAPPED]"

    output_lines.append(line)

    # Process children
    children = sorted(willow_children.get(class_id, []),
                      key=lambda x: willow_info.get(x, {}).get('name', x))
    for child_id in children:
        print_tree(child_id, willow_children, willow_info, existing_mappings,
                   mapped_info, mapped_children, indent + 1, visited, output_lines)

    return output_lines


def main():
    base_path = Path(__file__).parent.parent / 'data'

    print("Loading ontologies...")
    willow = load_json(base_path / 'ontologies' / 'willow.jsonld')
    mapped = load_json(base_path / 'ontologies' / 'mapped.json')
    mappings_data = load_json(base_path / 'Willow2Mapped.json')

    # Build graphs
    willow_children, willow_parents, willow_info = build_ontology_graph(willow)
    mapped_children, mapped_parents, mapped_info = build_ontology_graph(mapped)

    # Build existing mappings lookup
    existing_mappings = {m['InputDtmi']: m['OutputDtmi']
                         for m in mappings_data.get('InterfaceRemaps', [])}

    # Build reverse lookup for Mapped (normalized name -> id)
    mapped_by_name = {info['normalized']: id for id, info in mapped_info.items()}

    # Root classes for Willow
    roots = [
        ('Asset', 'dtmi:com:willowinc:Asset;1'),
        ('Collection', 'dtmi:com:willowinc:Collection;1'),
        ('Space', 'dtmi:com:willowinc:Space;1'),
    ]

    # Find suggestions for unmapped classes
    print("\n" + "=" * 80)
    print("HIERARCHY-BASED MAPPING SUGGESTIONS")
    print("=" * 80)

    suggestions = []

    for root_name, root_id in roots:
        descendants = get_descendants(root_id, willow_children)
        descendants.add(root_id)

        for willow_id in descendants:
            if willow_id not in existing_mappings:
                info = willow_info.get(willow_id, {})
                name = info.get('name', '')
                normalized = info.get('normalized', '')

                # First try direct name match
                if normalized in mapped_by_name:
                    suggestions.append({
                        'willow_id': willow_id,
                        'willow_name': name,
                        'mapped_id': mapped_by_name[normalized],
                        'mapped_name': mapped_info[mapped_by_name[normalized]]['name'],
                        'reason': 'exact name match'
                    })
                else:
                    # Try hierarchy-based match
                    suggested_id, reason = find_mapping_by_hierarchy(
                        willow_id, willow_info, willow_parents,
                        existing_mappings, mapped_children, mapped_info
                    )
                    if suggested_id:
                        suggestions.append({
                            'willow_id': willow_id,
                            'willow_name': name,
                            'mapped_id': suggested_id,
                            'mapped_name': mapped_info[suggested_id]['name'],
                            'reason': reason
                        })

    # Print suggestions
    print(f"\nFound {len(suggestions)} new mapping suggestions:\n")

    for s in sorted(suggestions, key=lambda x: x['willow_name']):
        print(f"{s['willow_name']}")
        print(f"  Willow:  {s['willow_id']}")
        print(f"  Mapped:  {s['mapped_id']}")
        print(f"  Reason:  {s['reason']}")
        print()

    # Output as JSON for easy addition
    print("\n" + "=" * 80)
    print("SUGGESTED MAPPINGS JSON:")
    print("=" * 80)
    for s in suggestions:
        print(f'{{"InputDtmi": "{s["willow_id"]}", "OutputDtmi": "{s["mapped_id"]}"}},')

    # Write tree to file
    print("\n" + "=" * 80)
    print("Writing hierarchy trees to files...")

    for root_name, root_id in roots:
        lines = print_tree(root_id, willow_children, willow_info, existing_mappings,
                          mapped_info, mapped_children)

        output_file = base_path / 'ontologies' / f'willow_{root_name.lower()}_mapping_tree.txt'
        with open(output_file, 'w') as f:
            f.write(f"WILLOW {root_name.upper()} HIERARCHY WITH MAPPINGS\n")
            f.write("=" * 60 + "\n\n")
            f.write('\n'.join(lines))

        print(f"  Wrote {output_file}")

    return suggestions


if __name__ == '__main__':
    suggestions = main()
