import json
import sys
import argparse

def sort_json_file(filepath):
    try:
        with open(filepath, 'r') as file:
            data = json.load(file)

        if 'InterfaceRemaps' in data and isinstance(data['InterfaceRemaps'], list):
            data['InterfaceRemaps'].sort(key=lambda x: x.get('InputDtmi', ''))

        with open(filepath, 'w') as file:
            json.dump(data, file, indent=2)

    except Exception as e:
        print(e)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='Sort mapping file script.')
    parser.add_argument('filepath', help='Path to the mapping file')

    args = parser.parse_args()

    sort_json_file(args.filepath)

if __name__ == "__main__":
    main()
