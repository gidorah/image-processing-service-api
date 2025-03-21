"""
Elasticsearch utilities for the image processing service.
"""
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ConnectionError, NotFoundError

logger = logging.getLogger(__name__)


class ElasticsearchClient:
    """
    Elasticsearch client for the image processing service.
    """

    def __init__(self):
        """
        Initialize the Elasticsearch client.
        """
        self.host = os.environ.get("ELASTIC_HOST", "elasticsearch")
        self.port = os.environ.get("ELASTIC_PORT", "9200")
        self.user = os.environ.get("ELASTIC_USER", "elastic")
        self.password = os.environ.get("ELASTIC_PASSWORD", "changeme")
        self.client = None
        self.connect()

    def connect(self) -> None:
        """
        Connect to Elasticsearch.
        """
        try:
            self.client = Elasticsearch(
                [f"http://{self.host}:{self.port}"],
                basic_auth=(self.user, self.password),
            )
            if self.client.ping():
                logger.info("Connected to Elasticsearch")
            else:
                logger.error("Failed to connect to Elasticsearch")
        except ConnectionError as e:
            logger.error(f"Failed to connect to Elasticsearch: {e}")
            self.client = None

    def create_index(self, index_name: str, mappings: Dict[str, Any]) -> bool:
        """
        Create an index with the given mappings.

        Args:
            index_name: The name of the index to create.
            mappings: The mappings for the index.

        Returns:
            bool: True if the index was created successfully, False otherwise.
        """
        if not self.client:
            logger.error("Elasticsearch client not initialized")
            return False

        try:
            if not self.client.indices.exists(index=index_name):
                self.client.indices.create(
                    index=index_name,
                    mappings=mappings,
                    settings={
                        "number_of_shards": 1,
                        "number_of_replicas": 0,
                    },
                )
                logger.info(f"Created index {index_name}")
                return True
            logger.info(f"Index {index_name} already exists")
            return True
        except Exception as e:
            logger.error(f"Failed to create index {index_name}: {e}")
            return False

    def index_document(
        self, index_name: str, document: Dict[str, Any], doc_id: Optional[str] = None
    ) -> bool:
        """
        Index a document in Elasticsearch.

        Args:
            index_name: The name of the index to index the document in.
            document: The document to index.
            doc_id: The ID of the document. If None, Elasticsearch will generate an ID.

        Returns:
            bool: True if the document was indexed successfully, False otherwise.
        """
        if not self.client:
            logger.error("Elasticsearch client not initialized")
            return False

        try:
            # Add timestamp if not present
            if "timestamp" not in document:
                document["timestamp"] = datetime.now().isoformat()

            if doc_id:
                self.client.index(index=index_name, id=doc_id, document=document)
            else:
                self.client.index(index=index_name, document=document)
            return True
        except Exception as e:
            logger.error(f"Failed to index document in {index_name}: {e}")
            return False

    def search(
        self, index_name: str, query: Dict[str, Any], size: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for documents in Elasticsearch.

        Args:
            index_name: The name of the index to search in.
            query: The query to search for.
            size: The maximum number of results to return.

        Returns:
            List[Dict[str, Any]]: The search results.
        """
        if not self.client:
            logger.error("Elasticsearch client not initialized")
            return []

        try:
            response = self.client.search(index=index_name, query=query, size=size)
            return [hit["_source"] for hit in response["hits"]["hits"]]
        except NotFoundError:
            logger.warning(f"Index {index_name} not found")
            return []
        except Exception as e:
            logger.error(f"Failed to search in {index_name}: {e}")
            return []


# Singleton instance
elasticsearch_client = ElasticsearchClient()
