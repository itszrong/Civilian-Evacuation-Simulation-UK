"""
Tests for services.storage_service module.
"""

import pytest
import json
import os
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, mock_open
from typing import Dict, Any, List

from services.storage_service import StorageService
from models.schemas import CanonicalDocument, ProvenanceRecord, AgentType, SourceTier, DocumentType
from core.config import Settings


class TestStorageService:
    """Test the StorageService class."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create test settings
        self.test_settings = Settings(
            DEBUG=True,
            LOCAL_STORAGE_PATH=self.temp_dir,
            S3_BUCKET=None,
            S3_ENDPOINT=None
        )
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('services.storage_service.get_settings')
    def test_initialization(self, mock_get_settings):
        """Test StorageService initialization."""
        mock_get_settings.return_value = self.test_settings
        
        service = StorageService()
        
        assert service.settings == self.test_settings
        
        # Check that directories were created
        base_path = Path(self.temp_dir)
        expected_dirs = ["raw", "norm", "index", "runs", "images", "logs"]
        
        for directory in expected_dirs:
            assert (base_path / directory).exists()
            assert (base_path / directory).is_dir()
        
        # Check provenance log file exists
        assert (base_path / "provenance.jsonl").exists()
    
    @patch('services.storage_service.get_settings')
    def test_store_document(self, mock_get_settings):
        """Test storing a canonical document."""
        mock_get_settings.return_value = self.test_settings
        service = StorageService()
        
        # Create test document
        now = datetime.now()
        document = CanonicalDocument(
            doc_id="test_doc_001",
            url="https://example.com/test",
            source="test_source",
            tier=SourceTier.GOV_PRIMARY,
            published_at=now,
            fetched_at=now,
            title="Test Document",
            text="This is test content for the document.",
            type=DocumentType.POLICY,
            jurisdiction="UK",
            entities=["London", "Transport"],
            hash="abc123def456"
        )
        
        # Store document
        stored_path = service.store_document(document, AgentType.FEEDS)
        
        assert stored_path is not None
        assert stored_path.endswith(".json")
        
        # Verify file was created
        full_path = Path(self.temp_dir) / stored_path
        assert full_path.exists()
        
        # Verify content
        with open(full_path, 'r') as f:
            stored_data = json.load(f)
        
        assert stored_data["doc_id"] == "test_doc_001"
        assert stored_data["title"] == "Test Document"
        assert stored_data["text"] == "This is test content for the document."
        assert stored_data["tier"] == "gov_primary"
    
    @patch('services.storage_service.get_settings')
    def test_store_document_with_provenance(self, mock_get_settings):
        """Test storing document creates provenance record."""
        mock_get_settings.return_value = self.test_settings
        service = StorageService()
        
        now = datetime.now()
        document = CanonicalDocument(
            doc_id="test_doc_002",
            url="https://example.com/test2",
            source="test_source",
            tier=SourceTier.NEWS_VERIFIED,
            published_at=now,
            fetched_at=now,
            title="Test Document 2",
            text="More test content.",
            type=DocumentType.NEWS,
            jurisdiction="UK",
            entities=[],
            hash="def456ghi789"
        )
        
        stored_path = service.store_document(document, AgentType.FEEDS)
        
        # Check provenance log
        provenance_path = Path(self.temp_dir) / "provenance.jsonl"
        assert provenance_path.exists()
        
        with open(provenance_path, 'r') as f:
            lines = f.readlines()
        
        # Should have at least one provenance record
        assert len(lines) >= 1
        
        # Parse last line (most recent record)
        last_record = json.loads(lines[-1])
        assert last_record["path"] == stored_path
        assert last_record["producer_agent"] == "feeds"
        assert last_record["source_url"] == "https://example.com/test2"
    
    @patch('services.storage_service.get_settings')
    def test_retrieve_document(self, mock_get_settings):
        """Test retrieving a stored document."""
        mock_get_settings.return_value = self.test_settings
        service = StorageService()
        
        # First store a document
        now = datetime.now()
        document = CanonicalDocument(
            doc_id="retrieve_test",
            url="https://example.com/retrieve",
            source="test_source",
            tier=SourceTier.GOV_PRIMARY,
            published_at=now,
            fetched_at=now,
            title="Retrieve Test Document",
            text="Content for retrieval test.",
            type=DocumentType.POLICY,
            jurisdiction="UK",
            entities=[],
            hash="retrieve123"
        )
        
        stored_path = service.store_document(document, AgentType.FEEDS)
        
        # Now retrieve it
        retrieved_doc = service.retrieve_document(stored_path)
        
        assert retrieved_doc is not None
        assert isinstance(retrieved_doc, CanonicalDocument)
        assert retrieved_doc.doc_id == "retrieve_test"
        assert retrieved_doc.title == "Retrieve Test Document"
        assert retrieved_doc.text == "Content for retrieval test."
    
    @patch('services.storage_service.get_settings')
    def test_retrieve_nonexistent_document(self, mock_get_settings):
        """Test retrieving a nonexistent document."""
        mock_get_settings.return_value = self.test_settings
        service = StorageService()
        
        retrieved_doc = service.retrieve_document("nonexistent/path.json")
        assert retrieved_doc is None
    
    @patch('services.storage_service.get_settings')
    def test_search_documents_basic(self, mock_get_settings):
        """Test basic document search functionality."""
        mock_get_settings.return_value = self.test_settings
        service = StorageService()
        
        # Store multiple documents
        documents = []
        for i in range(3):
            now = datetime.now()
            doc = CanonicalDocument(
                doc_id=f"search_test_{i}",
                url=f"https://example.com/search_{i}",
                source="test_source",
                tier=SourceTier.GOV_PRIMARY,
                published_at=now,
                fetched_at=now,
                title=f"Search Test Document {i}",
                text=f"This document contains search term evacuation and number {i}.",
                type=DocumentType.POLICY,
                jurisdiction="UK",
                entities=["London"] if i % 2 == 0 else ["Manchester"],
                hash=f"search{i}hash"
            )
            documents.append(doc)
            service.store_document(doc, AgentType.FEEDS)
        
        # Search for documents
        results = service.search_documents("evacuation", k=5)
        
        # Should find documents containing "evacuation"
        assert len(results) >= 1
        assert all("evacuation" in result.get("text", "").lower() for result in results)
    
    @patch('services.storage_service.get_settings')
    def test_search_documents_with_filters(self, mock_get_settings):
        """Test document search with tier and date filters."""
        mock_get_settings.return_value = self.test_settings
        service = StorageService()
        
        # Store documents with different tiers
        now = datetime.now()
        
        # Gov primary document
        gov_doc = CanonicalDocument(
            doc_id="gov_doc",
            url="https://gov.uk/test",
            source="gov_uk",
            tier=SourceTier.GOV_PRIMARY,
            published_at=now,
            fetched_at=now,
            title="Government Policy Document",
            text="Official government evacuation policy.",
            type=DocumentType.POLICY,
            jurisdiction="UK",
            entities=[],
            hash="govhash"
        )
        
        # News document
        news_doc = CanonicalDocument(
            doc_id="news_doc",
            url="https://news.com/test",
            source="news_source",
            tier=SourceTier.NEWS_VERIFIED,
            published_at=now,
            fetched_at=now,
            title="News Article",
            text="News about evacuation procedures.",
            type=DocumentType.NEWS,
            jurisdiction="UK",
            entities=[],
            hash="newshash"
        )
        
        service.store_document(gov_doc, AgentType.FEEDS)
        service.store_document(news_doc, AgentType.FEEDS)
        
        # Search with tier filter
        gov_results = service.search_documents(
            "evacuation",
            k=5,
            tiers=[SourceTier.GOV_PRIMARY]
        )
        
        # Should only return government documents
        assert len(gov_results) >= 1
        for result in gov_results:
            assert result.get("tier") == "gov_primary"
    
    @patch('services.storage_service.get_settings')
    def test_store_run_artifact(self, mock_get_settings):
        """Test storing run artifacts."""
        mock_get_settings.return_value = self.test_settings
        service = StorageService()
        
        run_id = "test_run_001"
        artifact_data = {
            "best_scenario": "scenario_001",
            "metrics": {
                "clearance_time": 1800.0,
                "max_queue": 150.0
            },
            "justification": "This scenario provides optimal evacuation routes."
        }
        
        stored_path = service.store_run_artifact(run_id, "memo.json", artifact_data, AgentType.JUDGE)
        
        assert stored_path is not None
        assert "runs" in stored_path
        assert run_id in stored_path
        assert "memo.json" in stored_path
        
        # Verify file was created
        full_path = Path(self.temp_dir) / stored_path
        assert full_path.exists()
        
        # Verify content
        with open(full_path, 'r') as f:
            stored_data = json.load(f)
        
        assert stored_data["best_scenario"] == "scenario_001"
        assert stored_data["metrics"]["clearance_time"] == 1800.0
    
    @patch('services.storage_service.get_settings')
    def test_retrieve_run_artifact(self, mock_get_settings):
        """Test retrieving run artifacts."""
        mock_get_settings.return_value = self.test_settings
        service = StorageService()
        
        run_id = "test_run_002"
        artifact_data = {"test": "data", "number": 42}
        
        # Store artifact
        stored_path = service.store_run_artifact(run_id, "test.json", artifact_data, AgentType.WORKER)
        
        # Retrieve artifact
        retrieved_data = service.retrieve_run_artifact(run_id, "test.json")
        
        assert retrieved_data is not None
        assert retrieved_data["test"] == "data"
        assert retrieved_data["number"] == 42
    
    @patch('services.storage_service.get_settings')
    def test_retrieve_nonexistent_run_artifact(self, mock_get_settings):
        """Test retrieving nonexistent run artifact."""
        mock_get_settings.return_value = self.test_settings
        service = StorageService()
        
        retrieved_data = service.retrieve_run_artifact("nonexistent_run", "nonexistent.json")
        assert retrieved_data is None
    
    @patch('services.storage_service.get_settings')
    def test_list_run_artifacts(self, mock_get_settings):
        """Test listing run artifacts."""
        mock_get_settings.return_value = self.test_settings
        service = StorageService()
        
        run_id = "test_run_003"
        
        # Store multiple artifacts
        artifacts = [
            ("memo.json", {"type": "memo"}),
            ("scenarios.json", {"type": "scenarios"}),
            ("results.json", {"type": "results"})
        ]
        
        for filename, data in artifacts:
            service.store_run_artifact(run_id, filename, data, AgentType.PLANNER)
        
        # List artifacts
        artifact_list = service.list_run_artifacts(run_id)
        
        assert len(artifact_list) == 3
        filenames = [artifact["filename"] for artifact in artifact_list]
        assert "memo.json" in filenames
        assert "scenarios.json" in filenames
        assert "results.json" in filenames
    
    @patch('services.storage_service.get_settings')
    def test_list_nonexistent_run_artifacts(self, mock_get_settings):
        """Test listing artifacts for nonexistent run."""
        mock_get_settings.return_value = self.test_settings
        service = StorageService()
        
        artifact_list = service.list_run_artifacts("nonexistent_run")
        assert artifact_list == []
    
    @patch('services.storage_service.get_settings')
    def test_calculate_file_hash(self, mock_get_settings):
        """Test file hash calculation."""
        mock_get_settings.return_value = self.test_settings
        service = StorageService()
        
        test_content = "This is test content for hashing."
        expected_hash = hashlib.sha256(test_content.encode()).hexdigest()
        
        calculated_hash = service._calculate_hash(test_content)
        assert calculated_hash == expected_hash
    
    @patch('services.storage_service.get_settings')
    def test_log_provenance(self, mock_get_settings):
        """Test provenance logging."""
        mock_get_settings.return_value = self.test_settings
        service = StorageService()
        
        # Log provenance record
        service._log_provenance(
            path="test/path.json",
            sha256="testhash123",
            size=1024,
            producer_agent=AgentType.FEEDS,
            source_url="https://example.com/source"
        )
        
        # Check provenance log
        provenance_path = Path(self.temp_dir) / "provenance.jsonl"
        assert provenance_path.exists()
        
        with open(provenance_path, 'r') as f:
            lines = f.readlines()
        
        assert len(lines) >= 1
        
        # Parse the record
        record = json.loads(lines[-1])
        assert record["path"] == "test/path.json"
        assert record["sha256"] == "testhash123"
        assert record["size"] == 1024
        assert record["producer_agent"] == "feeds"
        assert record["source_url"] == "https://example.com/source"
    
    @patch('services.storage_service.get_settings')
    def test_get_provenance_records(self, mock_get_settings):
        """Test retrieving provenance records."""
        mock_get_settings.return_value = self.test_settings
        service = StorageService()
        
        # Log multiple provenance records
        for i in range(3):
            service._log_provenance(
                path=f"test/path_{i}.json",
                sha256=f"hash{i}",
                size=1024 + i,
                producer_agent=AgentType.FEEDS,
                source_url=f"https://example.com/source_{i}"
            )
        
        # Get all records
        records = service.get_provenance_records()
        
        assert len(records) >= 3
        
        # Check that records are ProvenanceRecord objects
        for record in records:
            assert isinstance(record, ProvenanceRecord)
            assert record.producer_agent == AgentType.FEEDS
    
    @patch('services.storage_service.get_settings')
    def test_get_provenance_records_by_run(self, mock_get_settings):
        """Test retrieving provenance records filtered by run ID."""
        mock_get_settings.return_value = self.test_settings
        service = StorageService()
        
        run_id = "test_run_004"
        
        # Store run artifact (which logs provenance)
        service.store_run_artifact(run_id, "test.json", {"data": "test"}, AgentType.PLANNER)
        
        # Get records for this run
        records = service.get_provenance_records(run_id=run_id)
        
        assert len(records) >= 1
        for record in records:
            assert run_id in record.path
    
    @patch('services.storage_service.get_settings')
    def test_error_handling_corrupted_file(self, mock_get_settings):
        """Test error handling with corrupted files."""
        mock_get_settings.return_value = self.test_settings
        service = StorageService()
        
        # Create a corrupted JSON file
        corrupted_path = Path(self.temp_dir) / "corrupted.json"
        with open(corrupted_path, 'w') as f:
            f.write("invalid json content {")
        
        # Try to retrieve it
        retrieved_doc = service.retrieve_document("corrupted.json")
        assert retrieved_doc is None
    
    @patch('services.storage_service.get_settings')
    def test_error_handling_permission_denied(self, mock_get_settings):
        """Test error handling with permission issues."""
        mock_get_settings.return_value = self.test_settings
        
        # Create a directory we can't write to (if possible)
        restricted_dir = Path(self.temp_dir) / "restricted"
        restricted_dir.mkdir()
        
        try:
            # Try to make directory read-only
            restricted_dir.chmod(0o444)
            
            # Update settings to point to restricted directory
            restricted_settings = Settings(
                DEBUG=True,
                LOCAL_STORAGE_PATH=str(restricted_dir)
            )
            
            with patch('services.storage_service.get_settings', return_value=restricted_settings):
                # This should handle the permission error gracefully
                try:
                    service = StorageService()
                    # If it doesn't raise an exception, that's fine too
                except PermissionError:
                    # Expected behavior - should be handled gracefully
                    pass
        
        except (OSError, PermissionError):
            # If we can't set permissions, skip this test
            pytest.skip("Cannot test permission denied on this system")
        
        finally:
            # Restore permissions for cleanup
            try:
                restricted_dir.chmod(0o755)
            except (OSError, PermissionError):
                pass


@pytest.mark.integration
class TestStorageServiceIntegration:
    """Integration tests for StorageService."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_settings = Settings(
            DEBUG=True,
            LOCAL_STORAGE_PATH=self.temp_dir
        )
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('services.storage_service.get_settings')
    def test_full_document_lifecycle(self, mock_get_settings):
        """Test complete document storage and retrieval lifecycle."""
        mock_get_settings.return_value = self.test_settings
        service = StorageService()
        
        # Create and store document
        now = datetime.now()
        original_doc = CanonicalDocument(
            doc_id="lifecycle_test",
            url="https://example.com/lifecycle",
            source="test_source",
            tier=SourceTier.GOV_PRIMARY,
            published_at=now,
            fetched_at=now,
            title="Lifecycle Test Document",
            text="This document tests the full lifecycle.",
            type=DocumentType.POLICY,
            jurisdiction="UK",
            entities=["London", "Transport", "Emergency"],
            hash="lifecycle123"
        )
        
        # Store document
        stored_path = service.store_document(original_doc, AgentType.FEEDS)
        
        # Retrieve document
        retrieved_doc = service.retrieve_document(stored_path)
        
        # Verify all fields match
        assert retrieved_doc.doc_id == original_doc.doc_id
        assert retrieved_doc.url == original_doc.url
        assert retrieved_doc.source == original_doc.source
        assert retrieved_doc.tier == original_doc.tier
        assert retrieved_doc.title == original_doc.title
        assert retrieved_doc.text == original_doc.text
        assert retrieved_doc.type == original_doc.type
        assert retrieved_doc.jurisdiction == original_doc.jurisdiction
        assert retrieved_doc.entities == original_doc.entities
        assert retrieved_doc.hash == original_doc.hash
        
        # Search for document
        search_results = service.search_documents("lifecycle", k=5)
        assert len(search_results) >= 1
        
        # Verify provenance was logged
        provenance_records = service.get_provenance_records()
        assert len(provenance_records) >= 1
        
        lifecycle_records = [r for r in provenance_records if stored_path in r.path]
        assert len(lifecycle_records) == 1
        assert lifecycle_records[0].producer_agent == AgentType.FEEDS
    
    @patch('services.storage_service.get_settings')
    def test_full_run_artifact_lifecycle(self, mock_get_settings):
        """Test complete run artifact storage and retrieval lifecycle."""
        mock_get_settings.return_value = self.test_settings
        service = StorageService()
        
        run_id = "lifecycle_run"
        
        # Store multiple artifacts
        artifacts = {
            "memo.json": {
                "best_scenario": "scenario_001",
                "justification": "Optimal evacuation routes",
                "metrics": {"clearance_time": 1800.0}
            },
            "scenarios.json": {
                "scenarios": [
                    {"id": "scenario_001", "type": "flood"},
                    {"id": "scenario_002", "type": "fire"}
                ]
            },
            "results.json": {
                "results": [
                    {"scenario_id": "scenario_001", "score": 0.95},
                    {"scenario_id": "scenario_002", "score": 0.87}
                ]
            }
        }
        
        # Store all artifacts
        stored_paths = {}
        for filename, data in artifacts.items():
            path = service.store_run_artifact(run_id, filename, data, AgentType.JUDGE)
            stored_paths[filename] = path
        
        # Retrieve all artifacts
        for filename, original_data in artifacts.items():
            retrieved_data = service.retrieve_run_artifact(run_id, filename)
            assert retrieved_data == original_data
        
        # List artifacts
        artifact_list = service.list_run_artifacts(run_id)
        assert len(artifact_list) == 3
        
        filenames = [artifact["filename"] for artifact in artifact_list]
        for expected_filename in artifacts.keys():
            assert expected_filename in filenames
        
        # Verify provenance for run
        run_provenance = service.get_provenance_records(run_id=run_id)
        assert len(run_provenance) == 3  # One for each artifact
        
        for record in run_provenance:
            assert run_id in record.path
            assert record.producer_agent == AgentType.JUDGE
