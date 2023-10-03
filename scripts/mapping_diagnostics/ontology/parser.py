import re
from typing import Union, Dict, List


class DTDLParser:
    def __init__(self, content: Union[Dict[str, Union[str, int, List, Dict]], List[Dict[str, Union[str, int, List, Dict]]]]):
        if not isinstance(content, (dict, list)):
            raise TypeError('Expected content to be a dictionary or list representing JSON.')
        self.content = content
        self.namespaces = set()
        self.interfaces = set()
        self.relationships = set()

    def extract_namespace(self, dtmi):
            match = re.match(r'(^dtmi:.*:)[^:]+;\d+$', dtmi)
            if match:
                namespace = match.group(1)
            else:
                raise ValueError(f"Invalid DTMI format: {dtmi}")
            self.namespaces.add(namespace)

    def parse(self):
        for item in self.content:
            if item['@type'] == 'Interface':
                self.extract_namespace(item['@id'])
                self.interfaces.add(item['@id'])
                if 'contents' in item:
                    for content in item['contents']:
                        if content['@type'] == 'Relationship':
                            self.relationships.add(content['name'])
