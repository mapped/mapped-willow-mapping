import json
import sys

def sort_json_file(file_path):
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)

        if 'InterfaceRemaps' in data and isinstance(data['InterfaceRemaps'], list):
            data['InterfaceRemaps'].sort(key=lambda x: x.get('InputDtmi', ''))

            with open(file_path, 'w') as file:
                json.dump(data, file, indent=2)

    except Exception as e:
        print(e)
        sys.exit(e)

sort_json_file('Ontologies.Mappings/src/Mappings/v1/Mapped/mapped_v1_dtdlv2_Willow.json')
sort_json_file('Ontologies.Mappings/src/Mappings/v1/Willow/willow_v1_dtdlv2_mapped.json')
