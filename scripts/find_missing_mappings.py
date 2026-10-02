#!/usr/bin/env python3
"""Find missing mappings between Willow and Mapped ontologies."""

import json
import re
from pathlib import Path
from collections import defaultdict


def load_json(filepath):
    with open(filepath, 'r') as f:
        return json.load(f)


def get_display_name(iface):
    """Extract display name from interface."""
    dn = iface.get('displayName', '')
    if isinstance(dn, dict):
        return dn.get('en', '')
    return dn


def normalize_name(name):
    """Normalize name for comparison (remove spaces, underscores, lowercase)."""
    return re.sub(r'[\s_-]', '', name).lower()


def build_willow_hierarchy(interfaces):
    """Build set of all Willow classes under Asset, Collection, Space."""
    # Build parent -> children map
    children_map = defaultdict(list)
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
            'extends': extends if isinstance(extends, list) else [extends] if extends else []
        }

        if isinstance(extends, list):
            for parent_id in extends:
                children_map[parent_id].append(iface_id)
        elif extends:
            children_map[extends].append(iface_id)

    # Get all descendants of Asset, Collection, Space
    roots = [
        'dtmi:com:willowinc:Asset;1',
        'dtmi:com:willowinc:Collection;1',
        'dtmi:com:willowinc:Space;1'
    ]

    def get_descendants(class_id, visited=None):
        if visited is None:
            visited = set()
        if class_id in visited:
            return set()
        visited.add(class_id)

        result = {class_id}
        for child_id in children_map.get(class_id, []):
            result.update(get_descendants(child_id, visited))
        return result

    all_classes = set()
    for root in roots:
        all_classes.update(get_descendants(root))
        all_classes.add(root)  # Include roots themselves

    return all_classes, id_to_info


def build_mapped_lookup(interfaces):
    """Build lookup of Mapped classes by normalized name."""
    lookup = {}
    id_to_info = {}

    for iface in interfaces:
        iface_id = iface.get('@id', '')
        display_name = get_display_name(iface)

        if not display_name:
            display_name = iface_id.split(':')[-1].replace(';1', '')

        normalized = normalize_name(display_name)
        lookup[normalized] = iface_id
        id_to_info[iface_id] = {
            'id': iface_id,
            'name': display_name
        }

    return lookup, id_to_info


def main():
    base_path = Path(__file__).parent.parent / 'data'

    # Load ontologies
    print("Loading ontologies...")
    willow = load_json(base_path / 'ontologies' / 'willow.jsonld')
    mapped = load_json(base_path / 'ontologies' / 'mapped.json')

    # Load existing mappings
    mappings_data = load_json(base_path / 'Willow2Mapped.json')
    existing_mappings = {m['InputDtmi'] for m in mappings_data.get('InterfaceRemaps', [])}

    # Build Willow hierarchy
    print("Building Willow hierarchy...")
    willow_classes, willow_info = build_willow_hierarchy(willow)

    # Build Mapped lookup
    print("Building Mapped lookup...")
    mapped_lookup, mapped_info = build_mapped_lookup(mapped)

    # Find unmapped Willow classes
    unmapped = willow_classes - existing_mappings

    print(f"\nTotal Willow classes in hierarchy: {len(willow_classes)}")
    print(f"Already mapped: {len(existing_mappings & willow_classes)}")
    print(f"Unmapped: {len(unmapped)}")

    # Try to find matches for unmapped classes
    print("\n" + "="*80)
    print("POTENTIAL MAPPINGS")
    print("="*80)

    potential_mappings = []
    no_match = []

    for willow_id in sorted(unmapped):
        info = willow_info.get(willow_id, {})
        willow_name = info.get('name', willow_id)
        normalized = normalize_name(willow_name)

        # Try exact normalized match
        if normalized in mapped_lookup:
            mapped_id = mapped_lookup[normalized]
            potential_mappings.append({
                'willow_id': willow_id,
                'willow_name': willow_name,
                'mapped_id': mapped_id,
                'mapped_name': mapped_info[mapped_id]['name'],
                'match_type': 'exact'
            })
        else:
            # Try partial matches
            matches = []
            for mapped_norm, mapped_id in mapped_lookup.items():
                if normalized in mapped_norm or mapped_norm in normalized:
                    matches.append((mapped_id, mapped_info[mapped_id]['name']))

            if matches:
                # Take first match as suggestion
                potential_mappings.append({
                    'willow_id': willow_id,
                    'willow_name': willow_name,
                    'mapped_id': matches[0][0],
                    'mapped_name': matches[0][1],
                    'match_type': 'partial',
                    'other_matches': matches[1:5]  # Show up to 4 other matches
                })
            else:
                no_match.append({
                    'willow_id': willow_id,
                    'willow_name': willow_name
                })

    # Print exact matches
    exact_matches = [p for p in potential_mappings if p['match_type'] == 'exact']
    print(f"\n--- EXACT MATCHES ({len(exact_matches)}) ---")
    for p in exact_matches:
        print(f"  {p['willow_name']}")
        print(f"    Willow: {p['willow_id']}")
        print(f"    Mapped: {p['mapped_id']}")
        print()

    # Print partial matches
    partial_matches = [p for p in potential_mappings if p['match_type'] == 'partial']
    print(f"\n--- PARTIAL MATCHES ({len(partial_matches)}) ---")
    for p in partial_matches[:20]:  # Show first 20
        print(f"  {p['willow_name']} -> {p['mapped_name']} (partial)")
        print(f"    Willow: {p['willow_id']}")
        print(f"    Mapped: {p['mapped_id']}")
        if p.get('other_matches'):
            print(f"    Other options: {[m[1] for m in p['other_matches']]}")
        print()

    if len(partial_matches) > 20:
        print(f"  ... and {len(partial_matches) - 20} more partial matches")

    # Print no matches
    print(f"\n--- NO MATCH FOUND ({len(no_match)}) ---")
    for p in no_match[:30]:
        print(f"  {p['willow_name']}: {p['willow_id']}")
    if len(no_match) > 30:
        print(f"  ... and {len(no_match) - 30} more without matches")

    # Output exact matches as JSON for easy addition
    print("\n" + "="*80)
    print("EXACT MATCHES JSON (ready to add):")
    print("="*80)
    for p in exact_matches:
        print(f'    {{"InputDtmi": "{p["willow_id"]}", "OutputDtmi": "{p["mapped_id"]}"}},')

    return exact_matches, partial_matches, no_match


if __name__ == '__main__':
    main()
