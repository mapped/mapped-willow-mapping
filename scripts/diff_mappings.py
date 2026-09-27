import csv
import json
import sys

# Generated mapping files, compared against the same file names in the baseline directory.
MAPPING_FILES = {
    'Mapped2Willow': 'Ontologies.Mappings/src/Mappings/v1/Willow/Mapped2Willow.json',
    'Willow2Mapped': 'Ontologies.Mappings/src/Mappings/v1/Mapped/Willow2Mapped.json',
}
OUTPUT = 'scripts/output/mappings_diff.csv'
FIELDS = [
    'direction', 'change', 'input_dtmi',
    'old_output_dtmi', 'new_output_dtmi',
    'old_is_inferred', 'new_is_inferred',
    'old_confidence', 'new_confidence',
]


def diff(direction, old, new):
    rows = []
    # Non-InterfaceRemaps sections are only flagged, not diffed entry by entry.
    for section in sorted(set(old) | set(new)):
        if section != 'InterfaceRemaps' and old.get(section) != new.get(section):
            rows.append({'direction': direction, 'change': 'section_changed', 'input_dtmi': section})

    old_remaps = {r['InputDtmi']: r for r in old.get('InterfaceRemaps', [])}
    new_remaps = {r['InputDtmi']: r for r in new.get('InterfaceRemaps', [])}
    for dtmi in sorted(set(old_remaps) | set(new_remaps)):
        a, b = old_remaps.get(dtmi, {}), new_remaps.get(dtmi, {})
        if a == b:
            continue
        if not a:
            change = 'added'
        elif not b:
            change = 'removed'
        elif a['OutputDtmi'] != b['OutputDtmi']:
            change = 'target_changed'
        else:
            change = 'metadata_changed'  # IsInferred or Confidence
        rows.append({
            'direction': direction, 'change': change, 'input_dtmi': dtmi,
            'old_output_dtmi': a.get('OutputDtmi'), 'new_output_dtmi': b.get('OutputDtmi'),
            'old_is_inferred': a.get('IsInferred'), 'new_is_inferred': b.get('IsInferred'),
            'old_confidence': a.get('Confidence'), 'new_confidence': b.get('Confidence'),
        })
    return rows


def main():
    if len(sys.argv) != 2:
        sys.exit('usage: diff_mappings.py BASELINE_DIR  (holds Mapped2Willow.json and Willow2Mapped.json)')
    baseline_dir = sys.argv[1]

    rows = []
    for direction, path in MAPPING_FILES.items():
        with open(f'{baseline_dir}/{direction}.json') as f:
            old = json.load(f)
        with open(path) as f:
            new = json.load(f)
        rows += diff(direction, old, new)

    with open(OUTPUT, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f'{len(rows)} differences written to {OUTPUT}')


if __name__ == "__main__":
    main()
