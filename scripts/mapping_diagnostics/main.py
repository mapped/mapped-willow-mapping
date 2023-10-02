import json
from handler import DTDLHandler
from scripts.mapping_diagnostics.modules.mappings.mappings import Mappings 


def main():
    # Load ontologies
    mapped_ontology = DTDLHandler('mapped.ontologies.core.dtdl')
    mapped_ontology.process()
    willow_ontology = DTDLHandler('willowinc.ontology.dtdlv3')
    willow_ontology.process()

    # Load mappings
    mapped_mappings = Mappings('Ontologies.Mappings/src/Mappings/v1/Willow/mapped_v1_dtdlv2_Willow.json')
    mapped_mappings.parse()
    willow_mappings = Mappings('Ontologies.Mappings/src/Mappings/v1/Mapped/willow_v1_dtdlv2_mapped.json')
    willow_mappings.parse()

    # Find gaps
    missing_willow = set(willow_ontology.interfaces) - set(willow_mappings.interface_inputs)
    missing_mapped = set(mapped_ontology.interfaces) - set(mapped_mappings.interface_inputs)

    missing_gaps = {
        "missing_mapped_mappings": sorted(list(missing_mapped)),
        "missing_willow_mappings": sorted(list(missing_willow))
    }

    with open('mapping_gaps.json', 'w') as file:
        json.dump(missing_gaps, file, indent=2)

main()