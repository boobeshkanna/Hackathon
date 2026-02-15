from diagrams import Diagram, Cluster, Edge
from diagrams.aws.compute import Lambda
from diagrams.aws.integration import SQS
from diagrams.aws.network import APIGateway
from diagrams.aws.storage import S3
from diagrams.aws.database import Dynamodb
from diagrams.aws.ml import Sagemaker, SagemakerModel
from diagrams.aws.network import InternetGateway
from diagrams.onprem.client import Client

graph_attr = {
    "fontsize": "16",
    "bgcolor": "white",
    "rankdir": "LR",
    "splines": "ortho",
    "nodesep": "1.0",
    "ranksep": "1.5"
}

with Diagram("Story-to-Catalog Edge Node Architecture", 
             show=False, 
             direction="LR",
             graph_attr=graph_attr,
             filename="story_to_catalog_architecture"):
    
    # Cluster 1: Client Edge
    with Cluster("Client Edge"):
        mobile = Client("Android App\n(Zero-UI)")
    
    # Cluster 2: AWS Cloud
    with Cluster("AWS Cloud"):
        
        # Sub-Cluster 2A: Ingestion Layer
        with Cluster("Ingestion Layer"):
            api_gateway = APIGateway("Ingestion API")
        
        # Sub-Cluster 2B: Async Processing Pipeline
        with Cluster("Async Processing Pipeline"):
            queue = SQS("Async Event Queue")
            orchestrator = Lambda("Workflow\nOrchestrator")
        
        # Sub-Cluster 2C: AI & Transcreation Engine
        with Cluster("AI & Transcreation Engine"):
            vision_asr = Sagemaker("Vision & ASR Edge")
            transcreation = SagemakerModel("Transcreation LLM\n(Bedrock)")
        
        # Sub-Cluster 2D: State & Storage
        with Cluster("State & Storage"):
            raw_bucket = S3("Raw Media Bucket")
            enhanced_bucket = S3("Enhanced Assets\nBucket")
            metadata_db = Dynamodb("Catalog Metadata DB")
    
    # Cluster 3: External Network
    with Cluster("External Network"):
        ondc = InternetGateway("ONDC Network\nGateway")
    
    # Data Flow Connections
    mobile >> Edge(label="Uploads Image &\nVernacular Voice") >> api_gateway
    api_gateway >> Edge(label="Stores raw payload") >> raw_bucket
    api_gateway >> Edge(label="Triggers processing\nevent") >> queue
    queue >> Edge(label="Pulls event") >> orchestrator
    orchestrator >> Edge(label="Fetches raw media") >> raw_bucket
    orchestrator >> Edge(label="Sends audio/image\nfor processing") >> vision_asr
    vision_asr >> Edge(label="Returns Hindi/Telugu\nText & cleaned image") >> orchestrator
    orchestrator >> Edge(label="Sends text for\ntranscreation") >> transcreation
    transcreation >> Edge(label="Returns SEO English\ncopy & Beckn JSON") >> orchestrator
    orchestrator >> Edge(label="Saves processed\nimage") >> enhanced_bucket
    orchestrator >> Edge(label="Saves Beckn\npayload") >> metadata_db
    orchestrator >> Edge(label="Pushes finalized\ncatalog") >> ondc

print("Architecture diagram generated successfully!")
