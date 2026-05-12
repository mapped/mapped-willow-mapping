#!/usr/bin/env python3
"""Suggest mappings by finding candidates from parent mapping's subclasses."""

import json
import re
from pathlib import Path
from collections import defaultdict
from difflib import SequenceMatcher


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


def tokenize(name):
    """Split name into tokens for comparison."""
    # Split on spaces, underscores, and CamelCase
    name = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)
    return set(re.split(r'[\s_-]+', name.lower()))


def similarity_score(name1, name2):
    """Calculate similarity between two names."""
    # Normalized string similarity
    norm_score = SequenceMatcher(None, normalize_name(name1), normalize_name(name2)).ratio()

    # Token overlap score
    tokens1 = tokenize(name1)
    tokens2 = tokenize(name2)
    if tokens1 and tokens2:
        overlap = len(tokens1 & tokens2) / max(len(tokens1), len(tokens2))
    else:
        overlap = 0

    return (norm_score + overlap) / 2


def build_ontology_graph(interfaces):
    """Build parent->children and child->parents maps."""
    children_map = defaultdict(list)
    parents_map = defaultdict(list)
    id_to_info = {}

    for iface in interfaces:
        iface_id = iface.get('@id', '')
        extends = iface.get('extends', [])
        display_name = get_display_name(iface)
        description = iface.get('description', '')
        if isinstance(description, dict):
            description = description.get('en', '')

        if not display_name:
            display_name = iface_id.split(':')[-1].replace(';1', '')

        id_to_info[iface_id] = {
            'id': iface_id,
            'name': display_name,
            'normalized': normalize_name(display_name),
            'description': description
        }

        if isinstance(extends, list):
            for parent_id in extends:
                children_map[parent_id].append(iface_id)
                parents_map[iface_id].append(parent_id)
        elif extends:
            children_map[extends].append(iface_id)
            parents_map[iface_id].append(extends)

    return children_map, parents_map, id_to_info


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
        descendants.update(get_descendants(child_id, children_map, visited.copy()))
    return descendants


def get_nearest_mapped_ancestor(class_id, parents_map, existing_mappings):
    """Find the nearest ancestor that has a mapping."""
    visited = set()
    queue = list(parents_map.get(class_id, []))

    while queue:
        parent_id = queue.pop(0)
        if parent_id in visited:
            continue
        visited.add(parent_id)

        if parent_id in existing_mappings:
            return parent_id, existing_mappings[parent_id]

        queue.extend(parents_map.get(parent_id, []))

    return None, None


def main():
    base_path = Path(__file__).parent.parent / 'data'

    print("Loading ontologies...")
    willow = load_json(base_path / 'ontologies' / 'willow.jsonld')
    mapped = load_json(base_path / 'ontologies' / 'mapped.json')
    mappings_data = load_json(base_path / 'Willow2Mapped.json')

    # Build graphs
    willow_children, willow_parents, willow_info = build_ontology_graph(willow)
    mapped_children, mapped_parents, mapped_info = build_ontology_graph(mapped)

    # Existing mappings
    existing_mappings = {m['InputDtmi']: m['OutputDtmi']
                         for m in mappings_data.get('InterfaceRemaps', [])}

    # Get all Willow classes in hierarchy
    roots = [
        'dtmi:com:willowinc:Asset;1',
        'dtmi:com:willowinc:Collection;1',
        'dtmi:com:willowinc:Space;1',
    ]

    all_willow_classes = set()
    for root in roots:
        all_willow_classes.update(get_descendants(root, willow_children))
        all_willow_classes.add(root)

    # Find unmapped classes
    unmapped = all_willow_classes - set(existing_mappings.keys())

    print(f"\nTotal Willow classes: {len(all_willow_classes)}")
    print(f"Mapped: {len(existing_mappings.keys() & all_willow_classes)}")
    print(f"Unmapped: {len(unmapped)}")

    # For each unmapped class, find candidates
    suggestions = []

    for willow_id in sorted(unmapped, key=lambda x: willow_info.get(x, {}).get('name', x)):
        willow_name = willow_info.get(willow_id, {}).get('name', '')

        # Find nearest mapped ancestor
        ancestor_id, ancestor_mapping = get_nearest_mapped_ancestor(
            willow_id, willow_parents, existing_mappings)

        if not ancestor_mapping:
            continue

        ancestor_name = willow_info.get(ancestor_id, {}).get('name', '')
        mapped_ancestor_name = mapped_info.get(ancestor_mapping, {}).get('name', '')

        # Get all descendants of the mapped ancestor
        candidates = get_descendants(ancestor_mapping, mapped_children)
        candidates.add(ancestor_mapping)

        # Score candidates by similarity to Willow class name
        scored_candidates = []
        for cand_id in candidates:
            cand_name = mapped_info.get(cand_id, {}).get('name', '')
            score = similarity_score(willow_name, cand_name)
            scored_candidates.append({
                'id': cand_id,
                'name': cand_name,
                'score': score
            })

        # Sort by score descending
        scored_candidates.sort(key=lambda x: x['score'], reverse=True)
        top_candidates = scored_candidates[:5]  # Top 5

        # Determine best match
        best = top_candidates[0] if top_candidates else None
        if best and best['score'] > 0.5:  # Threshold for good match
            suggestions.append({
                'willow_id': willow_id,
                'willow_name': willow_name,
                'ancestor_willow': ancestor_name,
                'ancestor_mapped': mapped_ancestor_name,
                'best_match': best,
                'candidates': top_candidates,
                'confidence': 'high' if best['score'] > 0.8 else 'medium' if best['score'] > 0.6 else 'low'
            })

    # Print suggestions grouped by confidence
    high_conf = [s for s in suggestions if s['confidence'] == 'high']
    med_conf = [s for s in suggestions if s['confidence'] == 'medium']
    low_conf = [s for s in suggestions if s['confidence'] == 'low']

    print(f"\n{'='*80}")
    print(f"HIGH CONFIDENCE SUGGESTIONS ({len(high_conf)}) - Score > 0.8")
    print('='*80)
    for s in high_conf:
        print(f"\n{s['willow_name']} -> {s['best_match']['name']} (score: {s['best_match']['score']:.2f})")
        print(f"  Willow:  {s['willow_id']}")
        print(f"  Mapped:  {s['best_match']['id']}")
        print(f"  Parent:  {s['ancestor_willow']} -> {s['ancestor_mapped']}")

    print(f"\n{'='*80}")
    print(f"MEDIUM CONFIDENCE SUGGESTIONS ({len(med_conf)}) - Score 0.6-0.8")
    print('='*80)
    for s in med_conf[:30]:  # Limit output
        print(f"\n{s['willow_name']} -> {s['best_match']['name']} (score: {s['best_match']['score']:.2f})")
        print(f"  Willow:  {s['willow_id']}")
        print(f"  Mapped:  {s['best_match']['id']}")
        print(f"  Other candidates: {[c['name'] for c in s['candidates'][1:4]]}")
    if len(med_conf) > 30:
        print(f"\n  ... and {len(med_conf) - 30} more")

    # Output high confidence as JSON
    print(f"\n{'='*80}")
    print("HIGH CONFIDENCE MAPPINGS JSON (ready to add):")
    print('='*80)
    for s in high_conf:
        print(f'{{"InputDtmi": "{s["willow_id"]}", "OutputDtmi": "{s["best_match"]["id"]}"}},')

    return high_conf, med_conf, low_conf


if __name__ == '__main__':
    high, med, low = main()
