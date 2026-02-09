import os
import uuid
import time
from datetime import datetime
from dotenv import load_dotenv
from utils.gcp_client import gcp_client

def run_comprehensive_test():
    print("🚀 Starting Comprehensive GCP Service Test...")
    print(f"Project ID: {gcp_client.project_id}")
    print(f"Firestore DB: finsightcopilot")
    print(f"BigQuery Dataset: {gcp_client.dataset_id}")
    print("-" * 40)

    test_id = str(uuid.uuid4())[:8]
    results = {"firestore": False, "bigquery": False, "pubsub": False}

    # 1. Test Firestore
    print(f"📝 Testing Firestore (Session: test_{test_id})...")
    try:
        gcp_client.save_chat_message(f"test_{test_id}", "system", f"Comprehensive test round {test_id}")
        print("✅ Firestore: Message saved successfully.")
        results["firestore"] = True
    except Exception as e:
        print(f"❌ Firestore Error: {e}")

    # 2. Test BigQuery
    print(f"📝 Testing BigQuery (Log Activity)...")
    try:
        gcp_client.log_activity("TEST", "VerificationAgent", f"Testing connectivity {test_id}")
        print("✅ BigQuery: Activity logged successfully.")
        results["bigquery"] = True
    except Exception as e:
        print(f"❌ BigQuery Error: {e}")

    # 3. Test Pub/Sub
    print(f"📝 Testing Pub/Sub (Publish Completion)...")
    try:
        gcp_client.publish_analysis_complete("TEST", "verification", f"Test summary {test_id}")
        print("✅ Pub/Sub: Notification published successfully.")
        results["pubsub"] = True
    except Exception as e:
        print(f"❌ Pub/Sub Error: {e}")

    print("-" * 40)
    print("📋 Final Summary:")
    for service, status in results.items():
        print(f"{service.capitalize()}: {'✅ PASS' if status else '❌ FAIL'}")

    if all(results.values()):
        print("\n✨ All GCP services are working as per project needs!")
    else:
        print("\n⚠️ Some services failed verification. Please check the logs above.")

if __name__ == "__main__":
    run_comprehensive_test()
