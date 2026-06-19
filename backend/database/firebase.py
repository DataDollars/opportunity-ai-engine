import logging
import json
from typing import Dict, Any, List, Optional
import firebase_admin
from firebase_admin import credentials, firestore
from backend.config import settings

logger = logging.getLogger(__name__)

# --- Mock Firestore Client for Sandbox/Local Dry Run ---

class MockDocumentSnapshot:
    def __init__(self, doc_id: str, data: Optional[Dict[str, Any]]):
        self.id = doc_id
        self._data = data
        self.exists = data is not None

    def to_dict(self) -> Optional[Dict[str, Any]]:
        return self._data

    def get(self, field: str) -> Any:
        if self._data:
            return self._data.get(field)
        return None


class MockDocumentReference:
    def __init__(self, doc_id: str, collection_ref: "MockCollectionReference"):
        self.id = doc_id
        self.collection_ref = collection_ref

    def get(self, transaction=None) -> MockDocumentSnapshot:
        data = self.collection_ref.store.get(self.id)
        return MockDocumentSnapshot(self.id, data)

    def set(self, data: Dict[str, Any], merge: bool = False):
        if self.id not in self.collection_ref.store:
            self.collection_ref.store[self.id] = {}
        if merge:
            self.collection_ref.store[self.id].update(data)
        else:
            self.collection_ref.store[self.id] = dict(data)
        return None, self

    def update(self, data: Dict[str, Any]):
        if self.id not in self.collection_ref.store:
            raise Exception(f"Document {self.id} does not exist!")
        self.collection_ref.store[self.id].update(data)
        return None

    def delete(self):
        if self.id in self.collection_ref.store:
            del self.collection_ref.store[self.id]


class MockQuery:
    def __init__(self, collection_ref: "MockCollectionReference", filters: List[tuple] = None):
        self.collection_ref = collection_ref
        self.filters = filters or []
        self._limit: Optional[int] = None
        self._order_by: Optional[str] = None

    def where(self, filter=None, field_path: str = None, op_string: str = None, value: Any = None):
        new_filters = list(self.filters)
        if filter:
            # Handle FieldFilter object if passed
            try:
                # FieldFilter has field_path, op_string, value
                new_filters.append((filter.field_path, filter.op_string, filter.value))
            except AttributeError:
                pass
        elif field_path and op_string:
            new_filters.append((field_path, op_string, value))
        return MockQuery(self.collection_ref, new_filters)

    def order_by(self, field: str, direction: str = "ASCENDING"):
        self._order_by = field
        return self

    def limit(self, count: int):
        self._limit = count
        return self

    def stream(self) -> List[MockDocumentSnapshot]:
        results = []
        for doc_id, data in self.collection_ref.store.items():
            match = True
            for field, op, val in self.filters:
                doc_val = data.get(field)
                if op == "==" and doc_val != val:
                    match = False
                elif op == ">" and not (doc_val is not None and doc_val > val):
                    match = False
                elif op == "<" and not (doc_val is not None and doc_val < val):
                    match = False
                elif op == "in" and not (val is not None and doc_val in val):
                    match = False
                elif op == "array_contains" and not (isinstance(doc_val, list) and val in doc_val):
                    match = False
            if match:
                results.append(MockDocumentSnapshot(doc_id, data))
        
        if self._order_by:
            results.sort(key=lambda d: d.to_dict().get(self._order_by) or "")
        if self._limit:
            results = results[:self._limit]
        return results


class MockCollectionReference:
    def __init__(self, collection_name: str, db: "MockFirestoreClient"):
        self.name = collection_name
        self.db = db
        if collection_name not in self.db.store:
            self.db.store[collection_name] = {}
        self.store = self.db.store[collection_name]

    def document(self, doc_id: str) -> MockDocumentReference:
        return MockDocumentReference(doc_id, self)

    def add(self, data: Dict[str, Any]):
        import uuid
        doc_id = str(uuid.uuid4())
        self.store[doc_id] = dict(data)
        return None, MockDocumentReference(doc_id, self)

    def stream(self) -> List[MockDocumentSnapshot]:
        return [MockDocumentSnapshot(doc_id, data) for doc_id, data in self.store.items()]

    def where(self, filter=None, field_path: str = None, op_string: str = None, value: Any = None):
        q = MockQuery(self)
        return q.where(filter, field_path, op_string, value)


class MockFirestoreClient:
    def __init__(self):
        self.store: Dict[str, Dict[str, Any]] = {}

    def collection(self, collection_name: str) -> MockCollectionReference:
        return MockCollectionReference(collection_name, self)


# --- Firestore Initialization Engine ---

_db = None

def get_db():
    """
    Returns the Firestore DB client. Automatically falls back to a Mock
    Firestore client if credentials/initialization fail or are not supplied.
    """
    global _db
    if _db is not None:
        return _db

    try:
        # Check if already initialized in application context
        firebase_admin.get_app()
    except ValueError:
        # Initialize
        cred = None
        if settings.FIREBASE_CREDENTIALS:
            logger.info(f"Loading Firestore credentials from path: {settings.FIREBASE_CREDENTIALS}")
            cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS)
        elif settings.FIREBASE_CREDENTIALS_JSON:
            logger.info("Loading Firestore credentials from JSON env string")
            cred_dict = json.loads(settings.FIREBASE_CREDENTIALS_JSON)
            cred = credentials.Certificate(cred_dict)
        
        try:
            if cred:
                firebase_admin.initialize_app(cred, {
                    'projectId': settings.FIREBASE_PROJECT_ID
                })
            else:
                logger.info(f"Initializing Firebase with Project ID: {settings.FIREBASE_PROJECT_ID} (ADC)")
                firebase_admin.initialize_app(options={
                    'projectId': settings.FIREBASE_PROJECT_ID
                })
        except Exception as auth_err:
            logger.warning(f"Could not initialize Firebase Live client: {auth_err}. Falling back to Sandbox Mock.")
            _db = MockFirestoreClient()
            return _db

    try:
        # Try getting firestore client
        _db = firestore.client()
        logger.info("Successfully connected to live Firebase Firestore.")
    except Exception as e:
        logger.warning(f"Firestore Client could not be retrieved: {e}. Falling back to Sandbox Mock.")
        _db = MockFirestoreClient()

    return _db
