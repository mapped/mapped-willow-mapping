import json
import sys
import argparse

def sort_json_file(input_file_path, output_file_path):
    try:
        with open(input_file_path, 'r') as file:
            data = json.load(file)

        if 'InterfaceRemaps' in data and isinstance(data['InterfaceRemaps'], list):
            data['InterfaceRemaps'].sort(key=lambda x: x.get('InputDtmi', ''))

        with open(output_file_path, 'w') as file:
            json.dump(data, file, indent=2)

    except Exception as e:
        print(e)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='Sort JSON file script.')
    parser.add_argument('input_file', help='Path to the input JSON file')
    parser.add_argument('output_file', help='Path to the output JSON file')

    args = parser.parse_args()

    sort_json_file(args.input_file, args.output_file)

if __name__ == "__main__":
    main()
