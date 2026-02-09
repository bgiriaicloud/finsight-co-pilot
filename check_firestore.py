import os
import sys
from dotenv import load_dotenv
from google.cloud import firestore
from google.api_core.exceptions import PermissionDenied, NotFound

def test_firestore():
    load_dotenv()
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "fintech-ai-agent")
    db_id = "finsightcopilot"
    
    print(f"--- Firestore Diagnostic ---")
    print(f"Project ID: {project_id}")
    print(f"Database ID: {db_id}")
    print(f"Credentials File: {os.getenv('GOOGLE_APPLICATION_CREDENTIALS')}")
    
    try:
        db = firestore.Client(project=project_id, database=db_id)
        # Try to write a test document
        doc_ref = db.collection("_diagnostics").document("setup_check")
        doc_ref.set({"check": "ok", "timestamp": firestore.SERVER_TIMESTAMP})
        print("✅ SUCCESS: Successfully wrote to Firestore!")
        return True
    except NotFound:
        print(f"❌ ERROR: Managed database '{db_id}' was not found in project '{project_id}'.")
        print("Tip: Ensure you have created a database with this Name/ID in the GCP Console.")
    except PermissionDenied:
        print("❌ ERROR: Permission denied. Check if the Service Account has 'Cloud Datastore User' role.")
    except Exception as e:
        print(f"❌ ERROR: An unexpected error occurred: {e}")
    
    return False

if __name__ == "__main__":
    test_firestore()
