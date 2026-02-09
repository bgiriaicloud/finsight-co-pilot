import os
import uuid
import io
import time
from datetime import datetime
from dotenv import load_dotenv
from utils.gcp_client import gcp_client

def run_full_integration_test():
    print("🚀 Starting FULL GCP Integration Test Round...")
    print(f"Project ID: {gcp_client.project_id}")
    print(f"Firestore DB: finsightcopilot")
    print(f"BigQuery Dataset: {gcp_client.dataset_id}")
    print(f"GCS Bucket: {gcp_client.bucket_name}")
    print("-" * 50)

    test_id = str(uuid.uuid4())[:8]
    session_id = f"test_round_{test_id}"
    results = {
        "Firestore (Chat)": False,
        "BigQuery (Logging)": False,
        "GCS (Uploading)": False,
        "Pub/Sub (Notifying)": False
    }

    # 1. Firestore - Chat Message
    print(f"1️⃣  Testing Firestore: Saving dummy chat to session '{session_id}'...")
    try:
        gcp_client.save_chat_message(session_id, "user", "Hello, are you ready for the integration test?")
        gcp_client.save_chat_message(session_id, "assistant", f"Yes, beginning test round {test_id} now.")
        print("✅ Firestore: Chat messages saved successfully.")
        results["Firestore (Chat)"] = True
    except Exception as e:
        print(f"❌ Firestore Error: {e}")

    # 2. BigQuery - Agent Activity
    print(f"2️⃣  Testing BigQuery: Logging dummy activity for ticker 'DUMY'...")
    try:
        gcp_client.log_activity("DUMY", "VerificationBot", f"Integration test round {test_id} in progress")
        print("✅ BigQuery: Activity logged successfully.")
        results["BigQuery (Logging)"] = True
    except Exception as e:
        print(f"❌ BigQuery Error: {e}")

    # 3. GCS - Document Upload
    print(f"3️⃣  Testing GCS: Uploading dummy document 'test_doc_{test_id}.txt'...")
    try:
        dummy_content = f"Integration Test Report\nRound ID: {test_id}\nTimestamp: {datetime.now()}"
        file_stream = io.BytesIO(dummy_content.encode("utf-8"))
        url = gcp_client.upload_document(file_stream, f"tests/test_doc_{test_id}.txt")
        if url:
            print(f"✅ GCS: Document uploaded successfully. URL: {url}")
            results["GCS (Uploading)"] = True
        else:
            print("❌ GCS: Upload failed (no URL returned).")
    except Exception as e:
        print(f"❌ GCS Error: {e}")

    # 4. Pub/Sub - Completion Notification
    print(f"4️⃣  Testing Pub/Sub: Publishing completion for ticker 'DUMY'...")
    try:
        gcp_client.publish_analysis_complete("DUMY", "full_test", f"All systems tested in round {test_id}")
        print("✅ Pub/Sub: Notification published successfully.")
        results["Pub/Sub (Notifying)"] = True
    except Exception as e:
        print(f"❌ Pub/Sub Error: {e}")

    print("-" * 50)
    print("📊 FULL INTEGRATION SUMMARY:")
    all_passed = True
    for service, status in results.items():
        icon = "✅ PASS" if status else "❌ FAIL"
        print(f"{service:<20}: {icon}")
        if not status:
            all_passed = False

    if all_passed:
        print("\n✨ SUCCESS: All GCP services are working as expected by the project!")
    else:
        print("\n⚠️ WARNING: One or more services failed. Check the errors above.")

if __name__ == "__main__":
    run_full_integration_test()
