import json
import argparse

def read_mappings(file_path):
    with open(file_path) as rf:
        data = json.load(rf)
    return data

def reverse_mappings(mappings):
    rev_mappings = []
    for mapping in mappings:
        rev_mappings.append(
            {
                "InputDtmi": mapping['OutputDtmi'],
                "OutputDtmi": mapping['InputDtmi']
            }
        )
    return rev_mappings

def main():
    parser = argparse.ArgumentParser(description='Reverse mappings from a JSON file.')
    parser.add_argument('file_path', type=str, help='The path to the JSON file containing mappings.')
    args = parser.parse_args()

    mappings = read_mappings(args.file_path)
    reversed_mappings = reverse_mappings(mappings)

    output_file = 'reversed_mappings.json'
    with open(output_file, 'w') as wf:
        json.dump(reversed_mappings, wf, indent=4)

    print(f'Reversed mappings saved to {output_file}')

if __name__ == '__main__':
    main()

