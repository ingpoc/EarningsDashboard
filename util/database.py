from pymongo import MongoClient
import os
from functools import lru_cache

class DatabaseConnection:
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            mongodb_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
            cls._instance = MongoClient(mongodb_uri)
        return cls._instance
    
    @classmethod
    def get_db(cls, db_name='stock_data'):
        return cls.get_instance()[db_name]
    
    @classmethod
    def get_collection(cls, collection_name):
        return cls.get_db()[collection_name] 