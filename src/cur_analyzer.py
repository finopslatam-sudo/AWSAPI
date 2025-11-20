import boto3
import pandas as pd
from typing import Dict, List
from datetime import datetime, timedelta

class CURAnalyzer:
    def __init__(self):
        self.client = boto3.client('ce')
    
    def get_cost_and_usage_data(self, days: int = 30) -> Dict:
        """Obtiene datos detallados del CUR"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        response = self.client.get_cost_and_usage(
            TimePeriod={
                'Start': start_date.strftime('%Y-%m-%d'),
                'End': end_date.strftime('%Y-%m-%d')
            },
            Granularity='DAILY',
            Metrics=['UnblendedCost', 'UsageQuantity'],
            GroupBy=[
                {'Type': 'DIMENSION', 'Key': 'SERVICE'},
                {'Type': 'DIMENSION', 'Key': 'USAGE_TYPE'},
                {'Type': 'DIMENSION', 'Key': 'INSTANCE_TYPE'}
            ]
        )
        return response
    
    def analyze_cost_drivers(self) -> Dict:
        """Identifica los principales drivers de costo"""
        data = self.get_cost_and_usage_data()
        
        analysis = {
            'top_services': self._get_top_services(data),
            'cost_trends': self._analyze_cost_trends(data),
            'anomalies': self._detect_cost_anomalies(data)
        }
        
        return analysis
    
    def _get_top_services(self, data: Dict) -> List[Dict]:
        """Identifica los servicios más costosos"""
        services = {}
        for result in data['ResultsByTime']:
            for group in result['Groups']:
                service = group['Keys'][0]
                cost = float(group['Metrics']['UnblendedCost']['Amount'])
                if service in services:
                    services[service] += cost
                else:
                    services[service] = cost
        
        return sorted([{'service': k, 'cost': v} for k, v in services.items()], 
                     key=lambda x: x['cost'], reverse=True)[:10]