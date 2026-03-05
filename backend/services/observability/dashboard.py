"""
CloudWatch Dashboard Configuration

Creates CloudWatch dashboards for system health monitoring.

Requirements: 15.5
"""
import json
from typing import Dict, Any, List


def create_dashboard_body(region: str = 'us-east-1') -> str:
    """
    Create CloudWatch dashboard JSON configuration
    
    Args:
        region: AWS region
        
    Returns:
        JSON string for dashboard configuration
        
    Requirements: 15.5
    """
    dashboard_config = {
        "widgets": [
            # Queue Depth Widget
            {
                "type": "metric",
                "x": 0,
                "y": 0,
                "width": 12,
                "height": 6,
                "properties": {
                    "metrics": [
                        ["VernacularArtisanCatalog", "QueueDepth", {"stat": "Average"}],
                        ["...", {"stat": "Maximum"}]
                    ],
                    "view": "timeSeries",
                    "stacked": False,
                    "region": region,
                    "title": "Queue Depth",
                    "period": 300,
                    "yAxis": {
                        "left": {
                            "label": "Count"
                        }
                    }
                }
            },
            
            # Processing Latency Widget
            {
                "type": "metric",
                "x": 12,
                "y": 0,
                "width": 12,
                "height": 6,
                "properties": {
                    "metrics": [
                        ["VernacularArtisanCatalog", "ProcessingLatency", {"stat": "Average", "label": "Avg Latency"}],
                        ["...", {"stat": "p95", "label": "P95 Latency"}],
                        ["...", {"stat": "p99", "label": "P99 Latency"}]
                    ],
                    "view": "timeSeries",
                    "stacked": False,
                    "region": region,
                    "title": "Processing Latency",
                    "period": 300,
                    "yAxis": {
                        "left": {
                            "label": "Milliseconds"
                        }
                    },
                    "annotations": {
                        "horizontal": [
                            {
                                "label": "60s Threshold",
                                "value": 60000
                            }
                        ]
                    }
                }
            },
            
            # Error Rate Widget
            {
                "type": "metric",
                "x": 0,
                "y": 6,
                "width": 12,
                "height": 6,
                "properties": {
                    "metrics": [
                        ["VernacularArtisanCatalog", "ErrorCount", {"stat": "Sum", "label": "Total Errors"}],
                        [".", "SuccessCount", {"stat": "Sum", "label": "Total Successes"}]
                    ],
                    "view": "timeSeries",
                    "stacked": False,
                    "region": region,
                    "title": "Error vs Success Count",
                    "period": 300,
                    "yAxis": {
                        "left": {
                            "label": "Count"
                        }
                    }
                }
            },
            
            # Error Rate Percentage Widget
            {
                "type": "metric",
                "x": 12,
                "y": 6,
                "width": 12,
                "height": 6,
                "properties": {
                    "metrics": [
                        [{"expression": "100 * (m1 / (m1 + m2))", "label": "Error Rate %", "id": "e1"}],
                        ["VernacularArtisanCatalog", "ErrorCount", {"stat": "Sum", "id": "m1", "visible": False}],
                        [".", "SuccessCount", {"stat": "Sum", "id": "m2", "visible": False}]
                    ],
                    "view": "timeSeries",
                    "stacked": False,
                    "region": region,
                    "title": "Error Rate Percentage",
                    "period": 600,
                    "yAxis": {
                        "left": {
                            "label": "Percentage",
                            "min": 0,
                            "max": 100
                        }
                    },
                    "annotations": {
                        "horizontal": [
                            {
                                "label": "5% Threshold",
                                "value": 5,
                                "fill": "above",
                                "color": "#ff0000"
                            }
                        ]
                    }
                }
            },
            
            # Per-Operation Latency Widget
            {
                "type": "metric",
                "x": 0,
                "y": 12,
                "width": 12,
                "height": 6,
                "properties": {
                    "metrics": [
                        ["VernacularArtisanCatalog", "ProcessingLatency", {"stat": "Average", "dimensions": {"Operation": "upload"}}],
                        ["...", {"dimensions": {"Operation": "sagemaker"}}],
                        ["...", {"dimensions": {"Operation": "bedrock"}}],
                        ["...", {"dimensions": {"Operation": "ondc_submission"}}]
                    ],
                    "view": "timeSeries",
                    "stacked": False,
                    "region": region,
                    "title": "Latency by Operation",
                    "period": 300,
                    "yAxis": {
                        "left": {
                            "label": "Milliseconds"
                        }
                    }
                }
            },
            
            # ONDC Submission Status Widget
            {
                "type": "metric",
                "x": 12,
                "y": 12,
                "width": 12,
                "height": 6,
                "properties": {
                    "metrics": [
                        ["VernacularArtisanCatalog", "ONDCSubmissionStatus", {"stat": "Sum", "dimensions": {"Status": "success"}}],
                        ["...", {"dimensions": {"Status": "failed"}}],
                        ["...", {"dimensions": {"Status": "retrying"}}]
                    ],
                    "view": "timeSeries",
                    "stacked": True,
                    "region": region,
                    "title": "ONDC Submission Status",
                    "period": 300,
                    "yAxis": {
                        "left": {
                            "label": "Count"
                        }
                    }
                }
            },
            
            # Processing Cost Widget
            {
                "type": "metric",
                "x": 0,
                "y": 18,
                "width": 12,
                "height": 6,
                "properties": {
                    "metrics": [
                        ["VernacularArtisanCatalog", "ProcessingCost", {"stat": "Average", "dimensions": {"Operation": "sagemaker"}}],
                        ["...", {"dimensions": {"Operation": "bedrock"}}],
                        ["...", {"dimensions": {"Operation": "total"}}]
                    ],
                    "view": "timeSeries",
                    "stacked": False,
                    "region": region,
                    "title": "Processing Cost per Entry (USD)",
                    "period": 300,
                    "yAxis": {
                        "left": {
                            "label": "USD"
                        }
                    },
                    "annotations": {
                        "horizontal": [
                            {
                                "label": "$0.50 Threshold",
                                "value": 0.50,
                                "fill": "above",
                                "color": "#ff9900"
                            }
                        ]
                    }
                }
            },
            
            # Lambda Duration Widget
            {
                "type": "metric",
                "x": 12,
                "y": 18,
                "width": 12,
                "height": 6,
                "properties": {
                    "metrics": [
                        ["AWS/Lambda", "Duration", {"stat": "Average", "dimensions": {"FunctionName": "artisan-catalog-orchestrator"}}],
                        ["...", {"stat": "Maximum"}],
                        ["...", {"dimensions": {"FunctionName": "artisan-catalog-api-handler"}}]
                    ],
                    "view": "timeSeries",
                    "stacked": False,
                    "region": region,
                    "title": "Lambda Duration",
                    "period": 300,
                    "yAxis": {
                        "left": {
                            "label": "Milliseconds"
                        }
                    },
                    "annotations": {
                        "horizontal": [
                            {
                                "label": "60s Threshold",
                                "value": 60000
                            }
                        ]
                    }
                }
            },
            
            # Lambda Errors Widget
            {
                "type": "metric",
                "x": 0,
                "y": 24,
                "width": 12,
                "height": 6,
                "properties": {
                    "metrics": [
                        ["AWS/Lambda", "Errors", {"stat": "Sum", "dimensions": {"FunctionName": "artisan-catalog-orchestrator"}}],
                        ["...", {"dimensions": {"FunctionName": "artisan-catalog-api-handler"}}]
                    ],
                    "view": "timeSeries",
                    "stacked": False,
                    "region": region,
                    "title": "Lambda Errors",
                    "period": 300,
                    "yAxis": {
                        "left": {
                            "label": "Count"
                        }
                    }
                }
            },
            
            # SQS Queue Metrics Widget
            {
                "type": "metric",
                "x": 12,
                "y": 24,
                "width": 12,
                "height": 6,
                "properties": {
                    "metrics": [
                        ["AWS/SQS", "ApproximateNumberOfMessagesVisible", {"stat": "Average", "dimensions": {"QueueName": "catalog-processing-queue"}}],
                        [".", "ApproximateAgeOfOldestMessage", {"stat": "Maximum", "yAxis": "right"}]
                    ],
                    "view": "timeSeries",
                    "stacked": False,
                    "region": region,
                    "title": "SQS Queue Metrics",
                    "period": 300,
                    "yAxis": {
                        "left": {
                            "label": "Messages"
                        },
                        "right": {
                            "label": "Age (seconds)"
                        }
                    }
                }
            }
        ]
    }
    
    return json.dumps(dashboard_config)


def get_dashboard_widgets() -> List[Dict[str, Any]]:
    """
    Get list of dashboard widgets for programmatic access
    
    Returns:
        List of widget configurations
    """
    dashboard_json = create_dashboard_body()
    dashboard_dict = json.loads(dashboard_json)
    return dashboard_dict.get('widgets', [])
