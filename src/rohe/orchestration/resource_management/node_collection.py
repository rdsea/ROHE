class NodeCollection:
    def __init__(self, nodes=None):
        if nodes is None:
            self.collection = {}
        else:
            self.collection = nodes

    def add(self, node):
        self.collection[node.id] = node

    def remove(self, node_name):
        return self.collection.pop(node_name)

    def __str__(self):
        collection_info = ""
        for key in self.collection:
            collection_info = collection_info + str(self.collection[key]) + "\n"
        return collection_info

    def __repr__(self):
        collection_info = ""
        for key in self.collection:
            collection_info = collection_info + str(self.collection[key]) + "\n"
        return collection_info
