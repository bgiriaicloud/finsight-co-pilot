import os
import json
from google.cloud import firestore
from google.cloud import bigquery
from google.cloud import storage
from google.cloud import pubsub_v1
from google.api_core.exceptions import NotFound
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class GCPClient:
    def __init__(self):
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "fintech-ai-agent")
        self.dataset_id = "financial_copilot"
        self.topic_id = "analyst-events"
        self.sub_id = "analyst-events-bq-sub"
        self.bucket_name = os.getenv("GCS_BUCKET_NAME", "finai-docs-fintech-ai-agent")
        
        try:
            # Initialize clients
            self.db = firestore.Client(project=self.project_id, database="finsightcopilot")
            self.bq = bigquery.Client(project=self.project_id)
            self.storage = storage.Client(project=self.project_id)
            self.publisher = pubsub_v1.PublisherClient()
            self.subscriber = pubsub_v1.SubscriberClient()
            
            # Run infrastructure setup checks
            self._ensure_bq_setup()
            self._ensure_pubsub_topic()
            self._ensure_pubsub_subscription()
            
            print(f"✅ GCP Clients initialized for project: {self.project_id}")
            print(f"📦 Using bucket: {self.bucket_name}")
        except Exception as e:
            print(f"⚠️ Warning: GCP Client initialization failed: {e}")
            self.db = None
            self.bq = None
            self.storage = None
            self.publisher = None
            self.subscriber = None

    def _ensure_bq_setup(self):
        """Ensure BigQuery dataset and tables exist."""
        if not self.bq: return
        try:
            # Check/Create Dataset
            dataset_ref = bigquery.DatasetReference(self.project_id, self.dataset_id)
            try:
                self.bq.get_dataset(dataset_ref)
            except NotFound:
                dataset = bigquery.Dataset(dataset_ref)
                dataset.location = "US"
                self.bq.create_dataset(dataset)
                print(f"✅ Created BigQuery dataset: {self.dataset_id}")

            # 1. agent_logs table
            log_table_id = f"{self.project_id}.{self.dataset_id}.agent_logs"
            log_schema = [
                bigquery.SchemaField("ticker", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("agent", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("status", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("timestamp", "TIMESTAMP", mode="REQUIRED")
            ]
            try:
                self.bq.get_table(log_table_id)
            except NotFound:
                table = bigquery.Table(log_table_id, schema=log_schema)
                self.bq.create_table(table)
                print(f"✅ Created BigQuery table: agent_logs")

            # 2. analysis_results table (for Pub/Sub export)
            # When use_topic_schema=False, the table must contain a 'data' column
            # (which stores the JSON payload) or columns matching the JSON keys.
            # We also include columns for metadata because write_metadata=True.
            results_table_id = f"{self.project_id}.{self.dataset_id}.analysis_results"
            results_schema = [
                bigquery.SchemaField("data", "STRING", mode="NULLABLE"), # Raw JSON payload
                bigquery.SchemaField("ticker", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("agent", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("summary", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("timestamp", "TIMESTAMP", mode="NULLABLE"),
                bigquery.SchemaField("message_id", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("publish_time", "TIMESTAMP", mode="NULLABLE"),
                bigquery.SchemaField("attributes", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("subscription_name", "STRING", mode="NULLABLE"),
            ]
            try:
                table = self.bq.get_table(results_table_id)
                existing_fields = [f.name for f in table.schema]
                missing_fields = [f for f in results_schema if f.name not in existing_fields]
                if missing_fields:
                    new_schema = table.schema[:]
                    new_schema.extend(missing_fields)
                    table.schema = new_schema
                    self.bq.update_table(table, ["schema"])
                    print(f"✅ Updated BigQuery table {results_table_id} with missing columns")
            except NotFound:
                table = bigquery.Table(results_table_id, schema=results_schema)
                self.bq.create_table(table)
                print(f"✅ Created BigQuery table: analysis_results")

        except Exception as e:
            print(f"❌ BigQuery setup error: {e}")

    def _ensure_pubsub_topic(self):
        """Ensure the Pub/Sub topic exists."""
        if not self.publisher: return
        try:
            topic_path = self.publisher.topic_path(self.project_id, self.topic_id)
            try:
                self.publisher.get_topic(request={"topic": topic_path})
            except NotFound:
                self.publisher.create_topic(request={"topic": topic_path})
                print(f"✅ Created Pub/Sub topic: {self.topic_id}")
        except Exception as e:
            print(f"❌ Pub/Sub topic setup error: {e}")

    def _ensure_pubsub_subscription(self):
        """Ensure the Pub/Sub BigQuery subscription exists."""
        if not self.subscriber: return
        try:
            topic_path = self.publisher.topic_path(self.project_id, self.topic_id)
            sub_path = self.subscriber.subscription_path(self.project_id, self.sub_id)
            table_id = f"{self.project_id}:{self.dataset_id}.analysis_results"
            
            try:
                self.subscriber.get_subscription(request={"subscription": sub_path})
            except NotFound:
                bq_config = {
                    "table": table_id,
                    "write_metadata": True,
                    "use_topic_schema": False,
                    "drop_unknown_fields": True
                }
                request = {
                    "name": sub_path,
                    "topic": topic_path,
                    "bigquery_config": bq_config
                }
                self.subscriber.create_subscription(request=request)
                print(f"✅ Created Pub/Sub BigQuery subscription: {self.sub_id}")
        except Exception as e:
            print(f"❌ Pub/Sub subscription setup error: {e}")

    # --- Firestore Methods ---
    def save_chat_message(self, session_id, role, content):
        """Save a chat message to Firestore."""
        if not self.db: return
        try:
            data = {
                "role": role,
                "content": content,
                "timestamp": firestore.SERVER_TIMESTAMP
            }
            self.db.collection("chats").document(session_id).collection("messages").add(data)
        except Exception as e:
            print(f"❌ Firestore save error: {e}")

    # --- BigQuery Methods ---
    def log_activity(self, ticker, agent, status):
        """Log agent activity for analytics."""
        if not self.bq: return
        try:
            table_id = f"{self.project_id}.{self.dataset_id}.agent_logs"
            rows_to_insert = [{
                "ticker": ticker,
                "agent": agent,
                "status": status,
                "timestamp": datetime.utcnow().isoformat()
            }]
            errors = self.bq.insert_rows_json(table_id, rows_to_insert)
            if errors:
                print(f"❌ BigQuery insert errors: {errors}")
        except Exception as e:
            print(f"❌ BigQuery log error: {e}")

    # --- Storage Methods ---
    def upload_document(self, file_data, destination_name):
        """Upload reports or PDFs to GCS. file_data can be a path or a file-like object."""
        if not self.storage: return
        try:
            bucket = self.storage.bucket(self.bucket_name)
            blob = bucket.blob(destination_name)
            
            if isinstance(file_data, str) and os.path.exists(file_data):
                blob.upload_from_filename(file_data)
            else:
                # Seek to start if possible (for streamlit UploadedFile)
                if hasattr(file_data, "seek"):
                    file_data.seek(0)
                blob.upload_from_file(file_data)
                
            print(f"📤 Uploaded to GCS bucket '{self.bucket_name}': {destination_name}")
            return blob.public_url
        except Exception as e:
            print(f"❌ GCS upload error: {e}")
            return None

    # --- Pub/Sub Methods ---
    def publish_analysis_complete(self, ticker, agent_type, result_summary):
        """Notify external systems analysis is done."""
        if not self.publisher: return
        try:
            topic_path = self.publisher.topic_path(self.project_id, self.topic_id)
            message_data = {
                "ticker": ticker,
                "agent": agent_type,
                "summary": result_summary[:200] + "...",
                "timestamp": datetime.utcnow().isoformat()
            }
            data_str = json.dumps(message_data).encode("utf-8")
            self.publisher.publish(topic_path, data_str)
            print(f"📢 Pub/Sub notification sent for {ticker}")
        except Exception as e:
            print(f"❌ Pub/Sub publish error: {e}")

# Global instance
gcp_client = GCPClient()
