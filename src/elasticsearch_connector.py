"""
Connecteur Elasticsearch pour indexer les données de pression artérielle
"""

import os
import json
from datetime import datetime
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
import sys


class ElasticsearchConnector:
    """Classe pour gérer la connexion et l'indexation dans Elasticsearch"""
    
    def __init__(self):
        """Initialise la connexion à Elasticsearch"""
        self.es_host = os.getenv('ELASTICSEARCH_HOST', 'localhost')
        self.es_port = int(os.getenv('ELASTICSEARCH_PORT', '9200'))
        self.index_name = os.getenv('ELASTICSEARCH_INDEX', 'blood-pressure-observations')
        
        # Si ELASTICSEARCH_HOST est vide, ne pas essayer de se connecter
        if not self.es_host or self.es_host.strip() == "":
            pass  # Elasticsearch disabled
            self.es = None
            return
        
        try:
            # Construire l'URL complète pour Elasticsearch
            es_url = f'http://{self.es_host}:{self.es_port}'
            self.es = Elasticsearch(
                [es_url],
                timeout=30,
                max_retries=10,
                retry_on_timeout=True
            )
            
            # Vérifier la connexion
            if self.es.ping():
                self._create_index_if_not_exists()
            else:
                self.es = None
                
        except Exception as e:
            self.es = None
    
    def _create_index_if_not_exists(self):
        """Crée l'index Elasticsearch s'il n'existe pas"""
        if not self.es:
            return
        
        if not self.es.indices.exists(index=self.index_name):
            # Mapping pour les données de pression artérielle
            mapping = {
                "mappings": {
                    "properties": {
                        "observation_id": {"type": "keyword"},
                        "timestamp": {
                            "type": "date",
                            "format": "strict_date_optional_time||epoch_millis"
                        },
                        "patient_id": {"type": "keyword"},
                        "systolic": {"type": "integer"},
                        "diastolic": {"type": "integer"},
                        "heart_rate": {"type": "integer"},
                        "category": {"type": "keyword"},
                        "device_id": {"type": "keyword"},
                        "systolic_diastolic": {
                            "type": "text",
                            "fields": {
                                "keyword": {"type": "keyword"}
                            }
                        }
                    }
                },
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0
                }
            }
            
            self.es.indices.create(index=self.index_name, body=mapping)
            pass  # Index created
        else:
            pass  # Index already exists
    
    def index_observation(self, extracted_data):
        """
        Indexe une observation dans Elasticsearch
        
        Args:
            extracted_data: Données extraites de l'observation FHIR
        """
        if not self.es:
            return False
        
        try:
            # Préparer le document pour Elasticsearch
            doc = {
                "observation_id": extracted_data['observation_id'],
                "timestamp": extracted_data['timestamp'],
                "patient_id": extracted_data['patient_id'],
                "systolic": extracted_data['systolic'],
                "diastolic": extracted_data['diastolic'],
                "heart_rate": extracted_data['heart_rate'],
                "category": extracted_data['category'],
                "device_id": extracted_data['device_id'],
                "systolic_diastolic": f"{extracted_data['systolic']}/{extracted_data['diastolic']}"
            }
            
            # Indexer le document
            self.es.index(
                index=self.index_name,
                id=extracted_data['observation_id'],
                body=doc
            )
            
            return True
            
        except Exception as e:
            pass  # Error indexing (silent)
            return False
    
    def bulk_index_observations(self, observations_list):
        """
        Indexe plusieurs observations en une seule opération (plus efficace)
        
        Args:
            observations_list: Liste de données extraites
        """
        if not self.es:
            return False
        
        try:
            actions = []
            for extracted_data in observations_list:
                doc = {
                    "_index": self.index_name,
                    "_id": extracted_data['observation_id'],
                    "_source": {
                        "observation_id": extracted_data['observation_id'],
                        "timestamp": extracted_data['timestamp'],
                        "patient_id": extracted_data['patient_id'],
                        "systolic": extracted_data['systolic'],
                        "diastolic": extracted_data['diastolic'],
                        "heart_rate": extracted_data['heart_rate'],
                        "category": extracted_data['category'],
                        "device_id": extracted_data['device_id'],
                        "systolic_diastolic": f"{extracted_data['systolic']}/{extracted_data['diastolic']}"
                    }
                }
                actions.append(doc)
            
            bulk(self.es, actions)
            return True
            
        except Exception as e:
            pass  # Error bulk indexing (silent)
            return False
    
    def is_connected(self):
        """Vérifie si la connexion à Elasticsearch est active"""
        return self.es is not None and self.es.ping()
