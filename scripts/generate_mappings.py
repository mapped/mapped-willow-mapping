import json
import os
import pprint
from ontology_mapper.loader import NugetPackage
from ontology_mapper.engine import MappingEngine
from typing import Dict
import xml.etree.ElementTree as ET
from pdb import set_trace


def get_nuget_package(name: str, version: str):
    with NugetPackage(name) as package:
        ontology = package.get_content(version)
    return ontology

def get_package_version(package_name):
    tree = ET.parse('Ontologies.Mappings/test/Ontologies.Mappings.Test.csproj')
    root = tree.getroot()

    for package_ref in root.findall(".//PackageReference"):
        if package_ref.attrib.get('Include') == package_name:
            return package_ref.attrib.get('Version')

    return None

def get_dtdl_interfaces(ontology_content: Dict):
    interfaces = set()
    for item in ontology_content:
        if item['@type'] == 'Interface':
            interfaces.add(item['@id'])
    return interfaces


def main():
    mapped_version = get_package_version('Mapped.Ontologies.Core.Dtdl')
    mapped_ontology = get_nuget_package('Mapped.Ontologies.Core.Dtdl', mapped_version)
    willow_version = get_package_version('WillowInc.Ontology.DTDLv3')
    willow_ontology = get_nuget_package('WillowInc.Ontology.DTDLv3', willow_version)

    with open('data/Mapped2Willow.json') as file:
        mapped_mappings = json.load(file)

    with open('data/Willow2Mapped.json') as file:
        willow_mappings = json.load(file)

    root_mappings = {
        # Mapped
        "dtmi:org:brickschema:schema:Brick:Collection;1": ["dtmi:com:willowinc:Collection;1"],
        "dtmi:org:brickschema:schema:Brick:Point;1": ["dtmi:com:willowinc:Capability;1"],
        "dtmi:org:brickschema:schema:Brick:Alarm;1": ["dtmi:com:willowinc:State;1"],
        "dtmi:org:brickschema:schema:Brick:Command;1": ["dtmi:com:willowinc:Actuator;1"],
        "dtmi:org:brickschema:schema:Brick:Status;1": ["dtmi:com:willowinc:State;1", "dtmi:com:willowinc:Sensor;1"],
        "dtmi:org:brickschema:schema:Brick:Sensor;1": ["dtmi:com:willowinc:Sensor;1", "dtmi:com:willowinc:State;1"],
        "dtmi:org:brickschema:schema:Brick:Setpoint;1": ["dtmi:com:willowinc:Setpoint;1"],
        "dtmi:org:brickschema:schema:Brick:Location;1": ["dtmi:com:willowinc:Space;1"],
        "dtmi:org:brickschema:schema:Brick:Parameter;1": ["dtmi:com:willowinc:Parameter;1"],
        "dtmi:mapped:core:Thing;1": ["dtmi:com:willowinc:Asset;1"],

        # Willow
        "dtmi:com:willowinc:Collection;1": ["dtmi:org:brickschema:schema:Brick:Collection;1"],
        "dtmi:com:willowinc:Capability;1": ["dtmi:org:brickschema:schema:Brick:Point;1"],
        "dtmi:com:willowinc:Actuator;1": ["dtmi:org:brickschema:schema:Brick:Command;1"],
        "dtmi:com:willowinc:Sensor;1": ["dtmi:org:brickschema:schema:Brick:Sensor;1", "dtmi:org:brickschema:schema:Brick:Status;1"],
        "dtmi:com:willowinc:State;1": ["dtmi:org:brickschema:schema:Brick:Status;1", "dtmi:org:brickschema:schema:Brick:Sensor;1", "dtmi:org:brickschema:schema:Brick:Alarm;1"],
        "dtmi:com:willowinc:Setpoint;1": ["dtmi:org:brickschema:schema:Brick:Setpoint;1"],
        "dtmi:com:willowinc:Space;1": ["dtmi:org:brickschema:schema:Brick:Location;1"],
        "dtmi:com:willowinc:Parameter;1": ["dtmi:org:brickschema:schema:Brick:Parameter;1"],
        "dtmi:com:willowinc:Asset;1": ["dtmi:mapped:core:Thing;1"],

        # Exceptions 
        "dtmi:mapped:core:Billed_Electrical_Energy_Use;1": ["dtmi:com:willowinc:BilledActiveElectricalEnergy;1"],
        "dtmi:mapped:core:Billed_Electrical_Energy_Cost;1": ["dtmi:com:willowinc:BilledElectricalCost;1"],
        "dtmi:mapped:core:Utility_Bill;1": ["dtmi:com:willowinc:BilledUtilityCost;1"],
        "dtmi:com:willowinc:BilledActiveElectricalEnergy;1": ["dtmi:mapped:core:Billed_Electrical_Energy_Use;1"],
        "dtmi:com:willowinc:BilledElectricalCost;1": ["dtmi:mapped:core:Billed_Electrical_Energy_Cost;1"],
        "dtmi:com:willowinc:BilledUtilityCost;1": ["dtmi:mapped:core:Utility_Bill;1"],
    }

    engine_building = MappingEngine(
        mapped_ontology,
        mapped_mappings,
        willow_ontology,
        willow_mappings,
        root_mappings=root_mappings
    )

    engine_building.initialize_graph()
    valid, invalid_mappings = engine_building.validate()
    if not valid:
        formatted_mappings = pprint.pformat(invalid_mappings, indent=2)
        error_message = f"Invalid manual mappings found:\n{formatted_mappings}"
        raise Exception(error_message)
    
    _, inferable_nodes, uninferable_nodes = engine_building.classify_nodes() 
    engine_building.find_optimal_mappings(inferable_nodes)
    mapped_combined_mappings, willow_combined_mappings = engine_building.aggregate_mappings() 
    valid, invalid_inferred_mappings = engine_building.validate()
    for key, value in invalid_inferred_mappings.items():
        message = value['message']
        target = value['target']
        source_parents = value['parents']['source']
        target_parents = value['parents']['target']

        print(
            f"Warning for {key}\n"
            f"\t{message}\n"
            f"\tTarget: {target}\n"
            "\tSource Hierarchy:\n\t" +
            "\n\t".join(f"\t- {parent}" for parent in source_parents) +
            "\n\tTarget Hierarchy:\n\t" +
            "\n\t".join(f"\t- {parent}" for parent in target_parents) +
            f"\n"
        )
    
    willow_seen = set()
    for mapping in willow_combined_mappings:
        if mapping['InputDtmi'] not in willow_seen:
            willow_seen.add(mapping['InputDtmi'])

    mapped_seen = set()
    for mapping in mapped_combined_mappings:
        if mapping['InputDtmi'] not in mapped_seen:
            mapped_seen.add(mapping['InputDtmi'])

    if not os.path.exists('scripts/output'):
        os.makedirs('scripts/output')

    with open('scripts/output/missing.json', 'w') as f:
        json.dump(uninferable_nodes, f, indent=2)

    mapped_mappings['InterfaceRemaps'] = mapped_combined_mappings
    willow_mappings['InterfaceRemaps'] = willow_combined_mappings
    
    mapped_interfaces = get_dtdl_interfaces(mapped_ontology)
    mapped_missing_mappings = mapped_interfaces - mapped_seen
    willow_interfaces = get_dtdl_interfaces(willow_ontology)
    willow_missing_mappings = willow_interfaces - willow_seen 

    willow_dir = 'Ontologies.Mappings/src/Mappings/v1/Willow'
    mapped_dir = 'Ontologies.Mappings/src/Mappings/v1/Mapped'

    if not os.path.exists(willow_dir):
        os.makedirs(willow_dir)

    if not os.path.exists(mapped_dir):
        os.makedirs(mapped_dir)

    with open(f'{willow_dir}/Mapped2Willow.json', 'w') as f:
        json.dump(mapped_mappings, f, indent=2)

    with open(f'{mapped_dir}/Willow2Mapped.json', 'w') as f:
        json.dump(willow_mappings, f, indent=2)
    
    with open(f'scripts/output/mapped_missing_mappings.json', 'w') as f:
        json.dump(sorted(list(mapped_missing_mappings)), f, indent=2)

    with open(f'scripts/output/willow_missing_mappings.json', 'w') as f:
        json.dump(sorted(list(willow_missing_mappings)), f, indent=2)

if __name__ == "__main__":
    main()