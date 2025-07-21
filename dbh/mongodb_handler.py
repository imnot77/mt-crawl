from pymongo import MongoClient

class MongoDBHandler:
    def __init__(self, conn_str, db_name):
        self.client = MongoClient(conn_str)
        self.db = self.client[db_name]
    
    def insert_document(self, collection, data):
        self.db[collection].insert_one(data)
    
    def query_documents(self, collection, filter_cond):
        res = self.db[collection].find(filter_cond)
        return [{**doc, '_id': str(doc['_id'])} for doc in res]
    
    def update_document(self, collection, filter_cond, update_data):
        self.db[collection].update_one(filter_cond, update_data)
