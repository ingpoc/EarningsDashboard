from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import os
from functools import lru_cache
import logging

class DatabaseConnection:
    _instance = None
    _db = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            try:
                mongodb_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
                cls._instance = MongoClient(mongodb_uri)
                # Test connection
                cls._instance.admin.command('ismaster')
            except ConnectionFailure as e:
                logging.error(f"Failed to connect to MongoDB: {e}")
                raise
        return cls._instance
    
    @classmethod
    def get_db(cls, db_name='stock_data'):
        if cls._db is None:
            cls._db = cls.get_instance()[db_name]
        return cls._db
    
    @classmethod
    def get_collection(cls, collection_name):
        return cls.get_db()[collection_name]
    
    @classmethod
    def close_connection(cls):
        if cls._instance:
            cls._instance.close()
            cls._instance = None
            cls._db = None