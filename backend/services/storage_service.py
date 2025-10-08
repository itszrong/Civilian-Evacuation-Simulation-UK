"""
Storage service for London Evacuation Planning Tool.

This module handles sovereign storage with S3-compatible backends and local fallback,
including lineage tracking and provenance management.
"""

import json
import os
import hashlib
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import numpy as np
import pandas as pd

import structlog
from pydantic import BaseModel

from core.config import get_settings
from models.schemas import CanonicalDocument, ProvenanceRecord, AgentType

logger = structlog.get_logger(__name__)


class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle DataFrames and numpy types."""
    
    def default(self, obj):
        if isinstance(obj, pd.DataFrame):
            return {
                "type": "DataFrame",
                "data": obj.to_dict('records'),
                "columns": list(obj.columns),
                "shape": obj.shape
            }
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (np.integer, np.floating)):
            return obj.item()
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif pd.isna(obj):
            return None
        return super().default(obj)


class StorageService:
    """Service for sovereign storage with lineage tracking."""

    def __init__(self):
        self.settings = get_settings()
        self._setup_local_storage()

    def _setup_local_storage(self):
        """Set up local storage directories."""
        base_path = Path(self.settings.LOCAL_STORAGE_PATH)
        
        # Create directory structure
        directories = [
            "raw",
            "norm", 
            "index",
            "runs",
            "images",
            "logs"
        ]
        
        for directory in directories:
            dir_path = base_path / directory
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Create provenance log file if it doesn't exist
        provenance_file = base_path / "provenance.jsonl"
        if not provenance_file.exists():
            provenance_file.touch()

    async def store_document(self, document: CanonicalDocument, tier: str) -> str:
        """Store a canonical document with lineage tracking."""
        try:
            # Determine storage path based on tier and date
            date_str = document.fetched_at.strftime("%Y%m%d")
            
            # Store raw document
            raw_path = self._get_document_path("raw", tier, date_str, document.doc_id)
            await self._write_json_file(raw_path, document.dict())
            
            # Store normalized document (same as raw for now)
            norm_path = self._get_document_path("norm", tier, date_str, document.doc_id)
            await self._write_json_file(norm_path, document.dict())
            
            # Record provenance
            await self._record_provenance(
                path=str(norm_path),
                sha256=document.hash,
                size=len(document.text.encode()),
                producer_agent=AgentType.FEEDS,
                source_url=document.url
            )
            
            # Update source status
            await self._update_source_status(
                source=document.source,
                last_updated=document.fetched_at,
                documents_count=1,
                status="operational"
            )
            
            logger.debug("Document stored successfully", 
                        doc_id=document.doc_id, 
                        source=document.source)
            
            return str(norm_path)
            
        except Exception as e:
            logger.error("Failed to store document", 
                        doc_id=document.doc_id, 
                        error=str(e))
            
            # Update source status with error
            await self._update_source_status(
                source=document.source,
                last_error=str(e),
                status="error"
            )
            raise

    async def get_source_status(self, source_name: str) -> Dict[str, Any]:
        """Get status information for a data source."""
        status_file = Path(self.settings.LOCAL_STORAGE_PATH) / "logs" / f"{source_name}_status.json"
        
        if status_file.exists():
            try:
                with open(status_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error("Failed to read source status", 
                           source=source_name, 
                           error=str(e))
        
        # Return default status
        return {
            'source': source_name,
            'last_updated': None,
            'last_error': None,
            'documents_count': 0,
            'status': 'configured'
        }

    async def get_last_refresh_time(self) -> Optional[str]:
        """Get the timestamp of the last global refresh."""
        refresh_file = Path(self.settings.LOCAL_STORAGE_PATH) / "logs" / "last_refresh.txt"
        
        if refresh_file.exists():
            try:
                with open(refresh_file, 'r') as f:
                    return f.read().strip()
            except Exception:
                pass
        
        return None

    async def set_last_refresh_time(self, timestamp: datetime) -> None:
        """Set the timestamp of the last global refresh."""
        refresh_file = Path(self.settings.LOCAL_STORAGE_PATH) / "logs" / "last_refresh.txt"
        
        try:
            with open(refresh_file, 'w') as f:
                f.write(timestamp.isoformat())
        except Exception as e:
            logger.error("Failed to update refresh timestamp", error=str(e))

    async def store_run_artifact(self, run_id: str, artifact_type: str, 
                                data: Any, producer_agent: AgentType) -> str:
        """Store a run artifact with lineage tracking."""
        try:
            # Create run directory
            run_dir = Path(self.settings.LOCAL_STORAGE_PATH) / "runs" / run_id
            run_dir.mkdir(parents=True, exist_ok=True)
            
            # Determine file path based on artifact type
            if artifact_type == "scenario":
                file_path = run_dir / "scenarios" / f"{data.get('id', 'unknown')}.yml"
                file_path.parent.mkdir(exist_ok=True)
                content = self._dict_to_yaml(data)
            elif artifact_type == "result":
                file_path = run_dir / "results" / f"{data.get('scenario_id', 'unknown')}.json"
                file_path.parent.mkdir(exist_ok=True)
                content = json.dumps(data, indent=2, cls=CustomJSONEncoder)
            elif artifact_type == "memo":
                file_path = run_dir / "memo.json"
                content = json.dumps(data, indent=2, cls=CustomJSONEncoder)
            elif artifact_type == "city_simulation":
                # Store city-specific simulation results
                file_path = run_dir / "city_results" / f"{data.get('city', 'unknown')}.json"
                file_path.parent.mkdir(exist_ok=True)
                content = json.dumps(data, indent=2, cls=CustomJSONEncoder)
            elif artifact_type == "visualisation":
                # Store visualisation data (images, maps, etc.)
                city = data.get('city', 'unknown')
                file_path = run_dir / "visualisations" / f"{city}_visualisation.json"
                file_path.parent.mkdir(exist_ok=True)
                content = json.dumps(data, indent=2, cls=CustomJSONEncoder)
            elif artifact_type == "emergency_plan":
                # Store emergency response plans
                city = data.get('city', 'unknown')
                file_path = run_dir / "emergency_plans" / f"{city}_emergency_plan.json"
                file_path.parent.mkdir(exist_ok=True)
                content = json.dumps(data, indent=2, cls=CustomJSONEncoder)
            elif artifact_type == "scenarios":
                # Store multiple scenarios together
                file_path = run_dir / "scenarios.json"
                content = json.dumps(data, indent=2, cls=CustomJSONEncoder)
            elif artifact_type == "results":
                # Store multiple results together
                file_path = run_dir / "results.json"
                content = json.dumps(data, indent=2, cls=CustomJSONEncoder)
            elif artifact_type == "logs":
                file_path = run_dir / "logs.jsonl"
                content = json.dumps(data) + "\n"
            else:
                raise ValueError(f"Unknown artifact type: {artifact_type}")
            
            # Write file
            if artifact_type == "logs":
                # Append to logs file
                with open(file_path, 'a') as f:
                    f.write(content)
            else:
                with open(file_path, 'w') as f:
                    f.write(content)
            
            # Calculate hash and size
            file_hash = hashlib.sha256(content.encode()).hexdigest()
            file_size = len(content.encode())
            
            # Record provenance
            await self._record_provenance(
                path=str(file_path),
                sha256=file_hash,
                size=file_size,
                producer_agent=producer_agent,
                run_id=run_id
            )
            
            logger.debug("Run artifact stored", 
                        run_id=run_id, 
                        artifact_type=artifact_type, 
                        path=str(file_path))
            
            return str(file_path)
            
        except Exception as e:
            logger.error("Failed to store run artifact", 
                        run_id=run_id, 
                        artifact_type=artifact_type, 
                        error=str(e))
            # If it's a serialization error, try to clean the data
            if "not JSON serializable" in str(e):
                logger.warning("Attempting to clean non-serializable data")
                try:
                    cleaned_data = self._clean_data_for_serialization(data)
                    content = json.dumps(cleaned_data, indent=2, cls=CustomJSONEncoder)
                    file_path.write_text(content, encoding='utf-8')
                    logger.info("Successfully stored artifact after data cleaning")
                    return str(file_path)
                except Exception as clean_error:
                    logger.error("Failed to clean and store data", error=str(clean_error))
            raise

    async def get_run_metadata(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific run."""
        try:
            run_dir = Path(self.settings.LOCAL_STORAGE_PATH) / "runs" / run_id

            if not run_dir.exists():
                return None

            memo_file = run_dir / "memo.json"
            status = "completed" if memo_file.exists() else "in_progress"

            created_at = datetime.fromtimestamp(run_dir.stat().st_ctime)

            scenarios_dir = run_dir / "scenarios"
            scenario_count = len(list(scenarios_dir.glob("*.yml"))) if scenarios_dir.exists() else 0

            return {
                "run_id": run_id,
                "status": status,
                "created_at": created_at.isoformat(),
                "scenario_count": scenario_count
            }

        except Exception as e:
            logger.error("Failed to get run metadata", run_id=run_id, error=str(e))
            return None

    async def list_all_runs(self) -> List[Dict[str, Any]]:
        """List all runs from storage."""
        try:
            runs_dir = Path(self.settings.LOCAL_STORAGE_PATH) / "runs"

            if not runs_dir.exists():
                return []

            runs = []
            for run_path in runs_dir.iterdir():
                if not run_path.is_dir():
                    continue

                run_id = run_path.name

                memo_file = run_path / "memo.json"
                if memo_file.exists():
                    try:
                        with open(memo_file, 'r') as f:
                            memo_data = json.load(f)
                        status = "completed"
                    except Exception:
                        status = "unknown"
                else:
                    status = "in_progress"

                created_at = datetime.fromtimestamp(run_path.stat().st_ctime)

                scenarios_dir = run_path / "scenarios"
                scenario_count = len(list(scenarios_dir.glob("*.yml"))) if scenarios_dir.exists() else 0

                # Check for city simulation data
                city_results_dir = run_path / "city_results"
                city = None
                if city_results_dir.exists():
                    city_files = list(city_results_dir.glob("*.json"))
                    if city_files:
                        # Extract city from filename (e.g., "london.json" -> "london")
                        city = city_files[0].stem

                runs.append({
                    "run_id": run_id,
                    "status": status,
                    "created_at": created_at.isoformat(),
                    "scenario_count": scenario_count,
                    "city": city
                })

            runs.sort(key=lambda x: x["created_at"], reverse=True)
            return runs

        except Exception as e:
            logger.error("Failed to list runs", error=str(e))
            return []

    async def get_run_artifact(self, run_id: str, artifact_type: str,
                              item_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Retrieve a run artifact."""
        try:
            run_dir = Path(self.settings.LOCAL_STORAGE_PATH) / "runs" / run_id
            
            if artifact_type == "memo":
                file_path = run_dir / "memo.json"
            elif artifact_type == "city_simulation":
                city_results_dir = run_dir / "city_results"
                if not city_results_dir.exists():
                    return None

                json_files = list(city_results_dir.glob("*.json"))
                if not json_files:
                    return None

                with open(json_files[0], 'r') as f:
                    return json.load(f)
            elif artifact_type == "visualisation":
                viz_dir = run_dir / "visualisations"
                if not viz_dir.exists():
                    return None

                json_files = list(viz_dir.glob("*.json"))
                if not json_files:
                    return None

                with open(json_files[0], 'r') as f:
                    return json.load(f)
            elif artifact_type == "emergency_plan":
                # Retrieve emergency response plans
                emergency_dir = run_dir / "emergency_plans"
                if not emergency_dir.exists():
                    return None

                json_files = list(emergency_dir.glob("*.json"))
                if not json_files:
                    return None

                with open(json_files[0], 'r') as f:
                    return json.load(f)
            elif artifact_type == "scenarios":
                # First check for single scenarios.json file
                scenarios_file = run_dir / "scenarios.json"
                if scenarios_file.exists():
                    with open(scenarios_file, 'r') as f:
                        return json.load(f)

                # Fall back to individual scenario files
                if item_id:
                    file_path = run_dir / "scenarios" / f"{item_id}.yml"
                else:
                    # Return all scenarios from directory
                    scenarios_dir = run_dir / "scenarios"
                    if not scenarios_dir.exists():
                        return None

                    scenarios = []
                    for scenario_file in scenarios_dir.glob("*.yml"):
                        scenario_data = self._read_yaml_file(scenario_file)
                        scenarios.append(scenario_data)

                    return {"scenarios": scenarios, "total_count": len(scenarios)}
            elif artifact_type == "results":
                # First check for single results.json file
                results_file = run_dir / "results.json"
                if results_file.exists():
                    with open(results_file, 'r') as f:
                        return json.load(f)

                # Fall back to individual result files
                if item_id:
                    file_path = run_dir / "results" / f"{item_id}.json"
                else:
                    # Return all results from directory
                    results_dir = run_dir / "results"
                    if not results_dir.exists():
                        return None

                    results = []
                    for result_file in results_dir.glob("*.json"):
                        with open(result_file, 'r') as f:
                            result_data = json.load(f)
                        results.append(result_data)

                    return {"results": results, "total_count": len(results)}
            else:
                return None
            
            if file_path.exists():
                if artifact_type.endswith(".yml") or (artifact_type == "scenarios" and item_id):
                    return self._read_yaml_file(file_path)
                else:
                    with open(file_path, 'r') as f:
                        return json.load(f)
            
            return None
            
        except Exception as e:
            logger.error("Failed to get run artifact", 
                        run_id=run_id, 
                        artifact_type=artifact_type, 
                        error=str(e))
            return None

    async def search_documents(self, query: str, tier: Optional[str] = None, 
                             max_age_days: int = 7, limit: int = 10) -> List[Dict[str, Any]]:
        """Search stored documents (simple text search for now)."""
        try:
            results = []
            base_path = Path(self.settings.LOCAL_STORAGE_PATH) / "norm"
            
            # Search through normalized documents
            if tier:
                search_dirs = [base_path / tier]
            else:
                search_dirs = [d for d in base_path.iterdir() if d.is_dir()]
            
            cutoff_date = datetime.utcnow().timestamp() - (max_age_days * 24 * 3600)
            
            for tier_dir in search_dirs:
                if not tier_dir.is_dir():
                    continue
                
                for date_dir in tier_dir.iterdir():
                    if not date_dir.is_dir():
                        continue
                    
                    for doc_file in date_dir.glob("*.json"):
                        # Check file age
                        if doc_file.stat().st_mtime < cutoff_date:
                            continue
                        
                        try:
                            with open(doc_file, 'r') as f:
                                doc_data = json.load(f)
                            
                            # Simple text search
                            searchable_text = (
                                doc_data.get('title', '') + " " + 
                                doc_data.get('text', '')
                            ).lower()
                            
                            if query.lower() in searchable_text:
                                results.append({
                                    'doc_id': doc_data.get('doc_id'),
                                    'title': doc_data.get('title'),
                                    'url': doc_data.get('url'),
                                    'source': doc_data.get('source'),
                                    'published_at': doc_data.get('published_at'),
                                    'score': 1.0  # Simple scoring
                                })
                                
                                if len(results) >= limit:
                                    break
                        except Exception:
                            continue
                    
                    if len(results) >= limit:
                        break
                
                if len(results) >= limit:
                    break
            
            return results[:limit]
            
        except Exception as e:
            logger.error("Document search failed", 
                        query=query, 
                        error=str(e))
            return []

    def _get_document_path(self, storage_type: str, tier: str, 
                          date_str: str, doc_id: str) -> Path:
        """Get storage path for a document."""
        base_path = Path(self.settings.LOCAL_STORAGE_PATH)
        return base_path / storage_type / tier / date_str / f"{doc_id}.json"

    async def _write_json_file(self, file_path: Path, data: Dict[str, Any]) -> None:
        """Write JSON data to file."""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)

    def _read_yaml_file(self, file_path: Path) -> Dict[str, Any]:
        """Read YAML file."""
        import yaml
        with open(file_path, 'r') as f:
            return yaml.safe_load(f)

    def _dict_to_yaml(self, data: Dict[str, Any]) -> str:
        """Convert dictionary to YAML string."""
        import yaml
        return yaml.dump(data, default_flow_style=False)
    
    def _clean_data_for_serialization(self, data: Any) -> Any:
        """Recursively clean data to make it JSON serializable."""
        if isinstance(data, dict):
            return {k: self._clean_data_for_serialization(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._clean_data_for_serialization(item) for item in data]
        elif isinstance(data, pd.DataFrame):
            return {
                "type": "DataFrame_cleaned",
                "shape": data.shape,
                "columns": list(data.columns),
                "summary": "DataFrame removed for serialization"
            }
        elif isinstance(data, np.ndarray):
            return data.tolist()
        elif isinstance(data, (np.integer, np.floating)):
            return data.item()
        elif isinstance(data, np.bool_):
            return bool(data)
        elif pd.isna(data):
            return None
        else:
            return data

    async def _record_provenance(self, path: str, sha256: str, size: int,
                                producer_agent: AgentType, source_url: Optional[str] = None,
                                run_id: Optional[str] = None,
                                parent_hash: Optional[str] = None) -> None:
        """Record provenance information for an artifact."""
        try:
            provenance_record = ProvenanceRecord(
                run_id=run_id or "system",
                path=path,
                sha256=sha256,
                size=size,
                producer_agent=producer_agent,
                source_url=source_url,
                parent_hash=parent_hash,
                created_at=datetime.utcnow()
            )
            
            provenance_file = Path(self.settings.LOCAL_STORAGE_PATH) / "provenance.jsonl"
            
            with open(provenance_file, 'a') as f:
                f.write(provenance_record.json() + "\n")
                
        except Exception as e:
            logger.error("Failed to record provenance", 
                        path=path, 
                        error=str(e))

    async def _update_source_status(self, source: str, last_updated: Optional[datetime] = None,
                                   last_error: Optional[str] = None,
                                   documents_count: Optional[int] = None,
                                   status: Optional[str] = None) -> None:
        """Update status information for a data source."""
        try:
            status_file = Path(self.settings.LOCAL_STORAGE_PATH) / "logs" / f"{source}_status.json"
            
            # Load existing status
            if status_file.exists():
                with open(status_file, 'r') as f:
                    current_status = json.load(f)
            else:
                current_status = {
                    'source': source,
                    'last_updated': None,
                    'last_error': None,
                    'documents_count': 0,
                    'status': 'configured'
                }
            
            # Update fields
            if last_updated:
                current_status['last_updated'] = last_updated.isoformat()
            if last_error is not None:
                current_status['last_error'] = last_error
            if documents_count is not None:
                current_status['documents_count'] = current_status.get('documents_count', 0) + documents_count
            if status:
                current_status['status'] = status
            
            # Clear error if status is operational
            if status == 'operational':
                current_status['last_error'] = None
            
            # Write updated status
            status_file.parent.mkdir(parents=True, exist_ok=True)
            with open(status_file, 'w') as f:
                json.dump(current_status, f, indent=2)
                
        except Exception as e:
            logger.error("Failed to update source status", 
                        source=source, 
                        error=str(e))
