"""
Batch Processing Optimizer

Detects when multiple entries are queued and processes them in batches
to reduce costs and improve efficiency.

Requirements: 13.3, 19.3
"""
import logging
import concurrent.futures
from typing import List, Dict, Any
import boto3

from backend.lambda_functions.shared.config import config
from backend.lambda_functions.shared.logger import setup_logger

logger = setup_logger(__name__)

# Initialize SQS client
sqs_client = boto3.client('sqs', region_name=config.AWS_REGION)


class BatchProcessor:
    """
    Batch processing optimizer for catalog entries
    
    Requirements: 13.3, 19.3
    """
    
    BATCH_THRESHOLD = 5  # Minimum entries to trigger batch processing
    MAX_PARALLEL_WORKERS = 10  # Maximum parallel processing workers
    
    def __init__(self, queue_url: str):
        """
        Initialize batch processor
        
        Args:
            queue_url: SQS queue URL
        """
        self.queue_url = queue_url
    
    def check_queue_depth(self) -> int:
        """
        Check current queue depth
        
        Returns:
            Number of messages in queue
        """
        try:
            response = sqs_client.get_queue_attributes(
                QueueUrl=self.queue_url,
                AttributeNames=['ApproximateNumberOfMessages']
            )
            
            queue_depth = int(response['Attributes']['ApproximateNumberOfMessages'])
            logger.info(f"Current queue depth: {queue_depth}")
            return queue_depth
            
        except Exception as e:
            logger.error(f"Error checking queue depth: {e}")
            return 0
    
    def should_enable_batch_processing(self, current_batch_size: int) -> bool:
        """
        Determine if batch processing should be enabled
        
        Args:
            current_batch_size: Size of current batch
            
        Returns:
            True if batch processing should be enabled
            
        Requirements: 13.3
        """
        # Check if current batch meets threshold
        if current_batch_size >= self.BATCH_THRESHOLD:
            return True
        
        # Check queue depth
        queue_depth = self.check_queue_depth()
        if queue_depth >= self.BATCH_THRESHOLD:
            return True
        
        return False
    
    def process_batch_parallel(
        self,
        messages: List[Dict[str, Any]],
        process_func: callable
    ) -> List[Dict[str, Any]]:
        """
        Process batch of messages in parallel
        
        Args:
            messages: List of SQS messages
            process_func: Function to process each message
            
        Returns:
            List of results
            
        Requirements: 19.3
        """
        logger.info(f"Processing batch of {len(messages)} entries in parallel")
        
        results = []
        
        # Determine number of workers based on batch size
        num_workers = min(len(messages), self.MAX_PARALLEL_WORKERS)
        
        # Process in parallel using ThreadPoolExecutor
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            # Submit all tasks
            future_to_message = {
                executor.submit(process_func, msg): msg
                for msg in messages
            }
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_message):
                message = future_to_message[future]
                try:
                    result = future.result()
                    results.append(result)
                    logger.info(f"Completed processing: {message.get('tracking_id')}")
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    results.append({
                        'success': False,
                        'error': str(e),
                        'message': message
                    })
        
        logger.info(f"Batch processing completed: {len(results)} results")
        return results
    
    def optimize_batch_size(self, available_messages: int) -> int:
        """
        Determine optimal batch size based on available messages and resources
        
        Args:
            available_messages: Number of available messages
            
        Returns:
            Optimal batch size
        """
        # Start with smaller batches and scale up
        if available_messages < self.BATCH_THRESHOLD:
            return available_messages
        elif available_messages < 10:
            return self.BATCH_THRESHOLD
        elif available_messages < 50:
            return 10
        else:
            return 20  # Cap at 20 for Lambda timeout considerations
    
    def estimate_cost_savings(self, batch_size: int) -> Dict[str, float]:
        """
        Estimate cost savings from batch processing
        
        Args:
            batch_size: Size of batch
            
        Returns:
            Dict with cost estimates
        """
        # Rough estimates (adjust based on actual costs)
        individual_cost_per_entry = 0.05  # $0.05 per entry
        batch_cost_per_entry = 0.03  # $0.03 per entry in batch
        
        individual_total = batch_size * individual_cost_per_entry
        batch_total = batch_size * batch_cost_per_entry
        savings = individual_total - batch_total
        savings_percent = (savings / individual_total) * 100
        
        return {
            'individual_cost': individual_total,
            'batch_cost': batch_total,
            'savings': savings,
            'savings_percent': savings_percent
        }


def create_batch_processor() -> BatchProcessor:
    """Create batch processor instance"""
    return BatchProcessor(queue_url=config.SQS_QUEUE_URL)
