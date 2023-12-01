import json
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

engine.find_optimal_mappings(list(unmapped_nodes))
mapped_inferred_mappings, willow_inferred_mappings = engine.aggregate_normalized_mappings() 


willow_mappings['InterfaceRemaps'] = willow_manual_mappings + willow_inferred_mappings
mapped_mappings['InterfaceRemaps'] = mapped_manual_mappings + mapped_inferred_mappings

with open('Ontologies.Mappings/src/Mappings/v1/Willow/mapped_v1_dtdlv2_Willow.json', 'w') as f:
    json.dump(mapped_mappings, f, indent=2)

with open('Ontologies.Mappings/src/Mappings/v1/Mapped/willow_v1_dtdlv2_mapped.json', 'w') as f:
    json.dump(willow_mappings, f, indent=2)