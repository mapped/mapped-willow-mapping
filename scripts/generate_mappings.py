import json
import os
from collections import defaultdict
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

    engine = MappingEngine(
        mapped_ontology,
        mapped_mappings,
        willow_ontology,
        willow_mappings
    )

    engine.initialize_graph()
    engine.graph.add_node('dtmi:com:willowinc:airport:AirfieldLightingEquipment;1', ontology='willow')
    engine.graph.add_node('dtmi:com:willowinc:airport:Airport;1', ontology='willow')
    engine.graph.add_node('dtmi:com:willowinc:airport:AirportTerminal;1', ontology='willow')

    mapped_nodes = engine.get_nodes(criteria={'relationship': 'mapsTo'})
    unmapped_nodes = set(engine.get_nodes()) - set(mapped_nodes)
    engine.find_optimal_mappings(list(unmapped_nodes))
    mapped_inferred_mappings, willow_inferred_mappings, missing_mappings = engine.aggregate_mappings() 
    mapped_incoming_edges, willow_incoming_edges = engine.inspect()

    if not os.path.exists('scripts/output'):
        os.makedirs('scripts/output')

    with open('scripts/output/missing.json', 'w') as f:
        json.dump(missing_mappings, f, indent=2)

    with open('scripts/output/willow_incoming_edges.json', 'w') as f:
        json.dump(willow_incoming_edges, f, indent=2)

    with open('scripts/output/mapped_incoming_edges.json', 'w') as f:
        json.dump(mapped_incoming_edges, f, indent=2)

    mapped_mappings['InterfaceRemaps'] = mapped_inferred_mappings
    willow_mappings['InterfaceRemaps'] = willow_inferred_mappings

    willow_dir = 'Ontologies.Mappings/src/Mappings/v1/Willow'
    mapped_dir = 'Ontologies.Mappings/src/Mappings/v1/Mapped'

    if not os.path.exists(willow_dir):
        os.makedirs(willow_dir)

    if not os.path.exists(mapped_dir):
        os.makedirs(mapped_dir)

    with open('Ontologies.Mappings/src/Mappings/v1/Willow/mapped_v1_dtdlv2_Willow.json', 'w') as f:
        json.dump(mapped_mappings, f, indent=2)

    with open('Ontologies.Mappings/src/Mappings/v1/Mapped/willow_v1_dtdlv2_mapped.json', 'w') as f:
        json.dump(willow_mappings, f, indent=2)

if __name__ == "__main__":
    main()