import json
from ontology_mapper.loader import NugetPackage
from ontology_mapper.engine import MappingEngine
from ontology_mapper.mappers.proximity import ProximityMapper


with NugetPackage('mapped.ontologies.core.dtdl') as package:
    mapped_ontology = package.get_content('1.23.8')  # TODO: Remove specified version after "extends" is supported again

with open('Ontologies.Mappings/src/Mappings/v1/Willow/mapped_v1_dtdlv2_Willow.json') as file:
    mapped_mappings = json.load(file)

with NugetPackage('willowinc.ontology.dtdlv3') as package:
    willow_ontology = package.get_content()

with open('Ontologies.Mappings/src/Mappings/v1/Mapped/willow_v1_dtdlv2_mapped.json') as file:
    willow_mappings = json.load(file)

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
engine.save_inferred_mappings_to_json(mapped_inferred_mappings, 'mapped')
engine.save_inferred_mappings_to_json(willow_inferred_mappings, 'willow')
