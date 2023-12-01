import json
import os
from collections import defaultdict
from ontology_mapper.loader import NugetPackage
from ontology_mapper.engine import MappingEngine

with NugetPackage('mapped.ontologies.core.dtdl') as package:
    mapped_ontology = package.get_content('1.23.8')

with open('data/mapped_v1_dtdlv2_Willow.json') as file:
    mapped_mappings = json.load(file)
    mapped_manual_mappings = []
    for mapping in mapped_mappings['InterfaceRemaps']:
        if mapping.get('IsInferred', False) == False:
            mapping['IsInferred'] = False
            mapped_manual_mappings.append(mapping)

with NugetPackage('willowinc.ontology.dtdlv3') as package:
    willow_ontology = package.get_content()

with open('data/willow_v1_dtdlv2_mapped.json') as file:
    willow_mappings = json.load(file)
    willow_manual_mappings = []
    for mapping in willow_mappings['InterfaceRemaps']:
        if mapping.get('IsInferred', False) == False:
            mapping['IsInferred'] = False
            willow_manual_mappings.append(mapping)

engine = MappingEngine(
    mapped_ontology,
    mapped_mappings,
    willow_ontology,
    willow_mappings
)

engine.initialize_graph()

all_nodes = engine.get_nodes()
mapped_nodes = engine.get_nodes(criteria={'relationship': 'mapsTo'})
unmapped_nodes = set(all_nodes) - set(mapped_nodes)

# Calculate loss of granularity
from pdb import set_trace

def default_dict_value():
    return {'count': 0, 'nodes': []}

willow_incoming = defaultdict(default_dict_value)
mapped_incoming = defaultdict(default_dict_value)

for node in engine.graph.nodes(data=True):
    node_id, attributes = node
    for source_node, target_node, edge_data in engine.graph.edges(node_id, data=True):
        if edge_data['relationship'] == 'mapsTo':
            if attributes.get('ontology') == 'willow':
                mapped_incoming[target_node]['nodes'].append(source_node)
                mapped_incoming[target_node]['count'] += 1
            elif attributes.get('ontology') == 'mapped':
                willow_incoming[target_node]['nodes'].append(source_node)
                willow_incoming[target_node]['count'] += 1

for target_node in willow_incoming:
    willow_incoming[target_node]['nodes'].sort()

for target_node in mapped_incoming:
    mapped_incoming[target_node]['nodes'].sort()

willow_incoming = sorted(willow_incoming.items(), key=lambda x: x[1]['count'], reverse=True)
mapped_incoming = sorted(mapped_incoming.items(), key=lambda x: x[1]['count'], reverse=True)

if not os.path.exists('scripts/output'):
    os.makedirs('scripts/output')

with open('scripts/output/willow_incoming_edges.json', 'w') as f:
    json.dump(willow_incoming, f, indent=2)

with open('scripts/output/mapped_incoming_edges.json', 'w') as f:
    json.dump(mapped_incoming, f, indent=2)

engine.find_optimal_mappings(list(unmapped_nodes))
mapped_inferred_mappings, willow_inferred_mappings = engine.aggregate_normalized_mappings() 

source_mappings = []
source_mappings.extend([mapping['InputDtmi'] for mapping in mapped_manual_mappings])
source_mappings.extend([mapping['InputDtmi'] for mapping in mapped_inferred_mappings])
source_mappings.extend([mapping['InputDtmi'] for mapping in willow_manual_mappings])
source_mappings.extend([mapping['InputDtmi'] for mapping in willow_inferred_mappings])

unmapped = sorted(list(set(all_nodes) - set(source_mappings)))

with open('scripts/output/unmapped.json', 'w') as f:
    json.dump(unmapped, f, indent=2)

willow_mappings['InterfaceRemaps'] = willow_manual_mappings + willow_inferred_mappings
mapped_mappings['InterfaceRemaps'] = mapped_manual_mappings + mapped_inferred_mappings

with open('Ontologies.Mappings/src/Mappings/v1/Willow/mapped_v1_dtdlv2_Willow.json', 'w') as f:
    json.dump(mapped_mappings, f, indent=2)

with open('Ontologies.Mappings/src/Mappings/v1/Mapped/willow_v1_dtdlv2_mapped.json', 'w') as f:
    json.dump(willow_mappings, f, indent=2)