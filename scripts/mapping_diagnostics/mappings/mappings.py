import json
from typing import Dict, List

class Mappings:
    def __init__(self, mapping_file):
        self.mapping_file = mapping_file
        self.interface_mappings = []
        self.relationship_mappings = []
        self.namespace_mappings = []

    def parse(self) -> List[Dict[str, str]]:
        with open(self.mapping_file, 'r') as f:
            data = json.load(f)
            for mapping in data['InterfaceRemaps']:
                self.interface_mappings.append(
                    {
                        "Input": mapping['InputDtmi'],
                        "Output": mapping['OutputDtmi']
                    }
                )
            for mapping in data['RelationshipRemaps']:
                self.relationship_mappings.append(
                    {
                        "Input": mapping['InputRelationship'],
                        "Output": mapping['OutputRelationship'],
                        "ReverseDirection": mapping['ReverseRelationshipDirection'] 
                    }
                )
            for mapping in data['NamespaceRemaps']:
                self.namespace_mappings.append(
                    {
                        "Input": mapping['InputNamespace'],
                        "Output": mapping['OutputNamespace']
                    }
                )
    @property
    def interface_inputs(self):
        return [mapping['Input'] for mapping in self.interface_mappings]

    @property
    def interface_outputs(self):
        return [mapping['Output'] for mapping in self.interface_mappings]
        
    @property
    def relationship_inputs(self):
        return [mapping['Input'] for mapping in self.relationship_mappings]
    
    @property
    def relationship_outputs(self):
        return [mapping['Output'] for mapping in self.relationship_mappings]

    @property
    def namespace_inputs(self):
        return [mapping['Input'] for mapping in self.namespace_mappings]
        
    @property
    def namespace_outputs(self):
        return [mapping['Output'] for mapping in self.namespace_mappings]
