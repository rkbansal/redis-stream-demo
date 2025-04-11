# worker.py - Python service that processes images from Redis stream
import json
import os
import time
import redis
from PIL import Image, ImageFilter
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configure Redis client
REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

# Stream details
STREAM_KEY = 'image-processing-jobs'
CONSUMER_GROUP = 'image-processors'
CONSUMER_NAME = f'worker-{os.getpid()}'
RESULTS_DIR = os.path.join(os.path.dirname(__file__), 'processed')

# Create results directory if it doesn't exist
if not os.path.exists(RESULTS_DIR):
    os.makedirs(RESULTS_DIR)

# Ensure consumer group exists
try:
    redis_client.xgroup_create(STREAM_KEY, CONSUMER_GROUP, id='0', mkstream=True)
    logger.info(f"Created consumer group {CONSUMER_GROUP}")
except redis.exceptions.ResponseError as e:
    if 'BUSYGROUP' in str(e):
        logger.info(f"Consumer group {CONSUMER_GROUP} already exists")
    else:
        raise

def resize_image(image_path, width, height):
    """Resize the image to the specified dimensions."""
    with Image.open(image_path) as img:
        resized_img = img.resize((width, height))
        return resized_img

def convert_to_grayscale(image_path):
    """Convert the image to grayscale."""
    with Image.open(image_path) as img:
        grayscale_img = img.convert('L')
        return grayscale_img

def apply_blur(image_path, radius=2):
    """Apply Gaussian blur to the image."""
    with Image.open(image_path) as img:
        blurred_img = img.filter(ImageFilter.GaussianBlur(radius=radius))
        return blurred_img

def process_image(job_data):
    """Process the image according to the specified operation."""
    try:
        file_path = job_data['filePath']
        operation = job_data['operation']
        params = job_data['params']
        job_id = job_data['jobId']
        
        # Generate output path
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        filename, ext = os.path.splitext(os.path.basename(file_path))
        output_filename = f"{filename}_{operation}_{timestamp}{ext}"
        output_path = os.path.join(RESULTS_DIR, output_filename)
        
        # Process the image based on the operation
        processed_img = None
        
        if operation == 'resize':
            width = int(params.get('width', 800))
            height = int(params.get('height', 600))
            processed_img = resize_image(file_path, width, height)
            
        elif operation == 'grayscale':
            processed_img = convert_to_grayscale(file_path)
            
        elif operation == 'blur':
            radius = int(params.get('radius', 2))
            processed_img = apply_blur(file_path, radius)
            
        else:
            raise ValueError(f"Unsupported operation: {operation}")
        
        # Save the processed image
        processed_img.save(output_path)
        
        # Create a URL to access the processed image
        processed_image_url = f"/processed/{output_filename}"
        
        # Store the result in Redis
        result = {
            'status': 'completed',
            'jobId': job_id,
            'operation': operation,
            'processedImageUrl': processed_image_url,
            'completedAt': time.time()
        }
        
        redis_client.set(f"job-result:{job_id}", json.dumps(result))
        logger.info(f"Processed job {job_id}, operation: {operation}")
        
        return True
    except Exception as e:
        logger.error(f"Error processing job: {str(e)}")
        
        # Store error in Redis
        error_result = {
            'status': 'failed',
            'jobId': job_data.get('jobId', 'unknown'),
            'error': str(e),
            'completedAt': time.time()
        }
        
        redis_client.set(f"job-result:{job_data.get('jobId', 'unknown')}", json.dumps(error_result))
        return False

def process_pending_jobs():
    """Process any pending jobs from previous sessions."""
    try:
        # Look for pending messages for this consumer group
        pending = redis_client.xpending(STREAM_KEY, CONSUMER_GROUP)
        
        if pending[0] > 0:  # There are pending messages
            logger.info(f"Found {pending[0]} pending jobs")
            
            # Get pending message IDs
            pending_range = redis_client.xpending_range(
                STREAM_KEY, CONSUMER_GROUP, '-', '+', count=10
            )
            
            for p in pending_range:
                message_id = p['message_id']
                
                # Claim and process the message
                claimed = redis_client.xclaim(
                    STREAM_KEY, CONSUMER_GROUP, CONSUMER_NAME,
                    min_idle_time=60000, message_ids=[message_id]
                )
                
                if claimed:
                    message_id, message_data = claimed[0]
                    job_data = json.loads(message_data['jobData'])
                    logger.info(f"Processing pending job {job_data.get('jobId', 'unknown')}")
                    
                    if process_image(job_data):
                        redis_client.xack(STREAM_KEY, CONSUMER_GROUP, message_id)
    
    except Exception as e:
        logger.error(f"Error processing pending jobs: {str(e)}")

def main():
    """Main worker loop."""
    logger.info(f"Starting worker {CONSUMER_NAME}")
    
    # Process any pending jobs from previous runs
    process_pending_jobs()
    
    while True:
        try:
            # Read new messages from the stream
            messages = redis_client.xreadgroup(
                groupname=CONSUMER_GROUP,
                consumername=CONSUMER_NAME,
                streams={STREAM_KEY: '>'},  # '>' means only new messages
                count=1,
                block=5000  # Block for 5 seconds
            )
            
            if not messages:
                continue
                
            for stream, stream_messages in messages:
                for message_id, message_data in stream_messages:
                    job_data = json.loads(message_data['jobData'])
                    logger.info(f"Received job {job_data.get('jobId', 'unknown')}")
                    
                    # Process the image
                    if process_image(job_data):
                        # Acknowledge the message
                        redis_client.xack(STREAM_KEY, CONSUMER_GROUP, message_id)
            
        except KeyboardInterrupt:
            logger.info("Shutting down worker")
            break
            
        except Exception as e:
            logger.error(f"Error in worker loop: {str(e)}")
            time.sleep(1)  # Prevent tight error loops

if __name__ == "__main__":
    main()