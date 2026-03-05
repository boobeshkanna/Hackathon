"""
Amazon Transcribe ASR Service

Uses AWS Transcribe for audio transcription without requiring a trained model.
Supports Indian languages including Hindi, Tamil, Telugu, etc.
"""
import logging
import time
import uuid
from typing import Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class TranscriptionService:
    """Service for audio transcription using Amazon Transcribe"""
    
    # Supported Indian languages in Amazon Transcribe
    SUPPORTED_LANGUAGES = {
        'hi': 'hi-IN',  # Hindi
        'ta': 'ta-IN',  # Tamil
        'te': 'te-IN',  # Telugu
        'mr': 'mr-IN',  # Marathi
        # Note: Not all Indian languages are supported by Transcribe
        # For unsupported languages, you may need to use Bedrock or other services
    }
    
    def __init__(self, region: str = 'ap-south-1', s3_bucket: Optional[str] = None):
        """
        Initialize Transcribe client
        
        Args:
            region: AWS region
            s3_bucket: S3 bucket for temporary audio storage (required for Transcribe)
        """
        self.transcribe_client = boto3.client('transcribe', region_name=region)
        self.s3_client = boto3.client('s3', region_name=region)
        self.s3_bucket = s3_bucket
        self.region = region
        
        if not s3_bucket:
            # Use default bucket name
            account_id = boto3.client('sts').get_caller_identity()['Account']
            self.s3_bucket = f'transcribe-temp-{region}-{account_id}'
            logger.warning(f"No S3 bucket provided, using default: {self.s3_bucket}")
    
    def transcribe_audio(
        self,
        audio_bytes: bytes,
        language_code: str = 'hi',
        audio_format: str = 'opus'
    ) -> Dict[str, Any]:
        """
        Transcribe audio using Amazon Transcribe
        
        Args:
            audio_bytes: Audio data as bytes
            language_code: Language code (hi, ta, te, mr)
            audio_format: Audio format (opus, mp3, wav)
            
        Returns:
            Dict containing transcription results
        """
        # Map language code to Transcribe language code
        transcribe_lang = self.SUPPORTED_LANGUAGES.get(language_code, 'hi-IN')
        
        if language_code not in self.SUPPORTED_LANGUAGES:
            logger.warning(
                f"Language {language_code} not supported by Transcribe, "
                f"falling back to Hindi (hi-IN)"
            )
        
        # Generate unique job name
        job_name = f"transcribe-{uuid.uuid4()}"
        s3_key = f"audio/{job_name}.{audio_format}"
        
        try:
            # Upload audio to S3
            logger.info(f"Uploading audio to s3://{self.s3_bucket}/{s3_key}")
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=s3_key,
                Body=audio_bytes
            )
            
            # Start transcription job
            media_uri = f"s3://{self.s3_bucket}/{s3_key}"
            logger.info(f"Starting transcription job: {job_name}")
            
            self.transcribe_client.start_transcription_job(
                TranscriptionJobName=job_name,
                Media={'MediaFileUri': media_uri},
                MediaFormat=audio_format,
                LanguageCode=transcribe_lang,
                Settings={
                    'ShowSpeakerLabels': False,
                    'MaxSpeakerLabels': 1
                }
            )
            
            # Wait for job to complete
            result = self._wait_for_job(job_name)
            
            # Cleanup S3
            self._cleanup_s3(s3_key)
            
            return result
            
        except ClientError as e:
            logger.error(f"Transcription error: {e}")
            # Cleanup on error
            try:
                self._cleanup_s3(s3_key)
            except:
                pass
            raise
    
    def _wait_for_job(self, job_name: str, max_wait: int = 300) -> Dict[str, Any]:
        """
        Wait for transcription job to complete
        
        Args:
            job_name: Transcription job name
            max_wait: Maximum wait time in seconds
            
        Returns:
            Transcription results
        """
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            response = self.transcribe_client.get_transcription_job(
                TranscriptionJobName=job_name
            )
            
            status = response['TranscriptionJob']['TranscriptionJobStatus']
            
            if status == 'COMPLETED':
                logger.info(f"Transcription job {job_name} completed")
                return self._parse_transcription_result(response)
            
            elif status == 'FAILED':
                failure_reason = response['TranscriptionJob'].get('FailureReason', 'Unknown')
                logger.error(f"Transcription job {job_name} failed: {failure_reason}")
                raise Exception(f"Transcription failed: {failure_reason}")
            
            # Wait before checking again
            time.sleep(2)
        
        # Timeout
        logger.error(f"Transcription job {job_name} timed out after {max_wait}s")
        raise TimeoutError(f"Transcription job timed out after {max_wait} seconds")
    
    def _parse_transcription_result(self, response: Dict) -> Dict[str, Any]:
        """
        Parse transcription result from Transcribe response
        
        Args:
            response: Transcribe job response
            
        Returns:
            Formatted transcription result
        """
        job = response['TranscriptionJob']
        transcript_uri = job['Transcript']['TranscriptFileUri']
        
        # Download transcript
        import requests
        transcript_response = requests.get(transcript_uri)
        transcript_data = transcript_response.json()
        
        # Extract text and confidence
        results = transcript_data.get('results', {})
        transcripts = results.get('transcripts', [])
        items = results.get('items', [])
        
        full_text = transcripts[0]['transcript'] if transcripts else ''
        
        # Calculate average confidence
        confidences = [
            float(item.get('alternatives', [{}])[0].get('confidence', 0))
            for item in items
            if item.get('type') == 'pronunciation'
        ]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        # Extract segments with timestamps
        segments = self._extract_segments(items)
        
        # Detect language
        language_code = job.get('LanguageCode', 'hi-IN')
        language = language_code.split('-')[0]  # Extract 'hi' from 'hi-IN'
        
        result = {
            'text': full_text,
            'language': language,
            'confidence': avg_confidence,
            'low_confidence': avg_confidence < 0.7,
            'requires_manual_review': avg_confidence < 0.7,
            'segments': segments
        }
        
        logger.info(
            f"Transcription: '{full_text[:50]}...' "
            f"(confidence: {avg_confidence:.2%})"
        )
        
        return result
    
    def _extract_segments(self, items: list) -> list:
        """
        Extract segments with timestamps from Transcribe items
        
        Args:
            items: Transcribe items
            
        Returns:
            List of segments
        """
        segments = []
        current_segment = []
        segment_start = None
        
        for item in items:
            if item.get('type') == 'pronunciation':
                word = item.get('alternatives', [{}])[0].get('content', '')
                confidence = float(item.get('alternatives', [{}])[0].get('confidence', 0))
                start_time = float(item.get('start_time', 0))
                end_time = float(item.get('end_time', 0))
                
                if segment_start is None:
                    segment_start = start_time
                
                current_segment.append({
                    'word': word,
                    'confidence': confidence,
                    'start': start_time,
                    'end': end_time
                })
                
                # Create segment every 5 words or at punctuation
                if len(current_segment) >= 5:
                    segments.append(self._create_segment(current_segment, segment_start))
                    current_segment = []
                    segment_start = None
        
        # Add remaining words as final segment
        if current_segment:
            segments.append(self._create_segment(current_segment, segment_start))
        
        return segments
    
    def _create_segment(self, words: list, start_time: float) -> Dict:
        """
        Create a segment from words
        
        Args:
            words: List of word dictionaries
            start_time: Segment start time
            
        Returns:
            Segment dictionary
        """
        text = ' '.join([w['word'] for w in words])
        end_time = words[-1]['end']
        avg_confidence = sum([w['confidence'] for w in words]) / len(words)
        
        return {
            'text': text,
            'start': start_time,
            'end': end_time,
            'confidence': avg_confidence,
            'low_confidence': avg_confidence < 0.7
        }
    
    def _cleanup_s3(self, s3_key: str):
        """
        Delete temporary audio file from S3
        
        Args:
            s3_key: S3 object key
        """
        try:
            logger.info(f"Cleaning up s3://{self.s3_bucket}/{s3_key}")
            self.s3_client.delete_object(
                Bucket=self.s3_bucket,
                Key=s3_key
            )
        except ClientError as e:
            logger.warning(f"Failed to cleanup S3 object: {e}")
    
    def delete_transcription_job(self, job_name: str):
        """
        Delete transcription job
        
        Args:
            job_name: Job name to delete
        """
        try:
            self.transcribe_client.delete_transcription_job(
                TranscriptionJobName=job_name
            )
            logger.info(f"Deleted transcription job: {job_name}")
        except ClientError as e:
            logger.warning(f"Failed to delete job: {e}")
