import json
import os
import pprint
from ontology_mapper.loader import NugetPackage
from ontology_mapper.engine import MappingEngine
import xml.etree.ElementTree as ET


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

def main():
    mapped_version = get_package_version('Mapped.Ontologies.Core.Dtdl')
    mapped_ontology = get_nuget_package('Mapped.Ontologies.Core.Dtdl', mapped_version)
    willow_version = get_package_version('WillowInc.Ontology.DTDLv3')
    willow_ontology = get_nuget_package('WillowInc.Ontology.DTDLv3', willow_version)

    with open('data/mapped_v1_dtdlv2_Willow.json') as file:
        mapped_mappings = json.load(file)

    with open('data/willow_v1_dtdlv2_mapped.json') as file:
        willow_mappings = json.load(file)

    root_mappings = {
        # Mapped
        "dtmi:org:brickschema:schema:Brick:Collection;1": ["dtmi:com:willowinc:Collection;1"],
        "dtmi:org:brickschema:schema:Brick:Point;1": ["dtmi:com:willowinc:Capability;1"],
        "dtmi:org:brickschema:schema:Brick:Command;1": ["dtmi:com:willowinc:Actuator;1"],
        "dtmi:org:brickschema:schema:Brick:Status;1": ["dtmi:com:willowinc:State;1"],
        "dtmi:org:brickschema:schema:Brick:Sensor;1": ["dtmi:com:willowinc:Sensor;1"],
        "dtmi:org:brickschema:schema:Brick:Setpoint;1": ["dtmi:com:willowinc:Setpoint;1"],
        "dtmi:org:brickschema:schema:Brick:Space;1": ["dtmi:com:willowinc:Space;1"],
        "dtmi:org:brickschema:schema:Brick:Parameter;1": ["dtmi:com:willowinc:Parameter;1"],
        "dtmi:mapped:core:Thing;1": ["dtmi:com:willowinc:Asset;1"],

        # Willow
        "dtmi:com:willowinc:Collection;1": ["dtmi:org:brickschema:schema:Brick:Collection;1"],
        "dtmi:com:willowinc:Capability;1": ["dtmi:org:brickschema:schema:Brick:Point;1"],
        "dtmi:com:willowinc:Actuator;1": ["dtmi:org:brickschema:schema:Brick:Command;1"],
        "dtmi:com:willowinc:Sensor;1": ["dtmi:org:brickschema:schema:Brick:Sensor;1"],
        "dtmi:com:willowinc:State;1": ["dtmi:org:brickschema:schema:Brick:Status;1"],
        "dtmi:com:willowinc:Setpoint;1": ["dtmi:org:brickschema:schema:Brick:Setpoint;1"],
        "dtmi:com:willowinc:Space;1": ["dtmi:org:brickschema:schema:Brick:Space;1"],
        "dtmi:com:willowinc:Parameter;1": ["dtmi:org:brickschema:schema:Brick:Parameter;1"],
        "dtmi:com:willowinc:Asset;1": ["dtmi:mapped:core:Thing;1"],

        # Exceptions 
        "dtmi:mapped:core:Billed_Electrical_Energy_Use;1": ["dtmi:com:willowinc:BilledActiveElectricalEnergy;1"],
        "dtmi:mapped:core:Billed_Electrical_Energy_Cost;1": ["dtmi:com:willowinc:BilledElectricalCost;1"],
        "dtmi:com:willowinc:BilledActiveElectricalEnergy;1": ["dtmi:mapped:core:Billed_Electrical_Energy_Use;1"],
        "dtmi:com:willowinc:BilledElectricalCost;1": ["dtmi:mapped:core:Billed_Electrical_Energy_Cost;1"],
    }

    engine = MappingEngine(
        mapped_ontology,
        mapped_mappings,
        willow_ontology,
        willow_mappings,
        root_mappings=root_mappings
    )

    engine.initialize_graph()
    engine.graph.add_node('dtmi:com:willowinc:airport:AirfieldLightingEquipment;1', ontology='willow')
    engine.graph.add_node('dtmi:com:willowinc:airport:Airport;1', ontology='willow')
    engine.graph.add_node('dtmi:com:willowinc:airport:AirportTerminal;1', ontology='willow')
    valid, invalid_mappings = engine.validate()
    if not valid:
        formatted_mappings = pprint.pformat(invalid_mappings, indent=2)
        error_message = f"Invalid manual mappings found:\n{formatted_mappings}"
        raise Exception(error_message)
    
    _, inferable_nodes, uninferable_nodes = engine.classify_nodes() 
    engine.find_optimal_mappings(inferable_nodes)
    mapped_combined_mappings, willow_combined_mappings = engine.aggregate_mappings() 
    mapped_incoming_edges, willow_incoming_edges = engine.inspect()
    valid, invalid_inferred_mappings = engine.validate()
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

    if not os.path.exists('scripts/output'):
        os.makedirs('scripts/output')

    with open('scripts/output/missing.json', 'w') as f:
        json.dump(uninferable_nodes, f, indent=2)

    with open('scripts/output/willow_incoming_edges.json', 'w') as f:
        json.dump(willow_incoming_edges, f, indent=2)

    with open('scripts/output/mapped_incoming_edges.json', 'w') as f:
        json.dump(mapped_incoming_edges, f, indent=2)

    mapped_mappings['InterfaceRemaps'] = mapped_combined_mappings
    willow_mappings['InterfaceRemaps'] = willow_combined_mappings

    willow_dir = 'Ontologies.Mappings/src/Mappings/v1/Willow'
    mapped_dir = 'Ontologies.Mappings/src/Mappings/v1/Mapped'

    if not os.path.exists(willow_dir):
        os.makedirs(willow_dir)

    if not os.path.exists(mapped_dir):
        os.makedirs(mapped_dir)

    with open(f'{willow_dir}/mapped_v1_dtdlv2_Willow.json', 'w') as f:
        json.dump(mapped_mappings, f, indent=2)

    with open(f'{mapped_dir}/willow_v1_dtdlv2_mapped.json', 'w') as f:
        json.dump(willow_mappings, f, indent=2)

if __name__ == "__main__":
    main()