import json
from handler import DTDLHandler
from mappings.mappings import Mappings 


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
    missing_willow_interfaces = set(willow_ontology.interfaces) - set(willow_mappings.interface_inputs)
    missing_mapped_interfaces = set(mapped_ontology.interfaces) - set(mapped_mappings.interface_inputs)
    missing_willow_relationships =  set(willow_ontology.relationships) - set(willow_mappings.relationship_inputs)
    missing_mapped_relationships =  set(mapped_ontology.relationships) - set(mapped_mappings.relationship_inputs)
    missing_willow_namespaces = set(willow_ontology.namespaces) - set(willow_mappings.relationship_inputs)
    missing_mapped_namespaces = set(mapped_ontology.namespaces) - set(mapped_mappings.namespace_inputs)

    gaps = {
        "mapped": {
            "missing_namespaces": sorted(list(missing_mapped_namespaces)),
            "missing_relationships": sorted(list(missing_mapped_relationships)),
            "missing_interfaces": sorted(list(missing_mapped_interfaces))
        },
        "willow": {
            "missing_namespaces": sorted(list(missing_willow_namespaces)),
            "missing_relationships": sorted(list(missing_willow_relationships)),
            "missing_interfaces": sorted(list(missing_willow_interfaces))
        }
    }

    with open('gaps.json', 'w') as file:
        json.dump(gaps, file, indent=2)

if __name__ == '__main__':
    main()