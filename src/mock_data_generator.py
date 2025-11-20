# src/mock_data_generator.py
import random
from datetime import datetime, timedelta
import json

class MockDataGenerator:
    def __init__(self):
        self.services = ['EC2', 'S3', 'RDS', 'Lambda', 'CloudWatch', 'EBS', 'Data Transfer']
        
    def generate_cost_data(self, days=30):
        """Genera datos de costos ficticios para testing"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        mock_data = {
            'ResultsByTime': [],
            'IsMockData': True
        }
        
        current_date = start_date
        while current_date <= end_date:
            # Generar costo diario aleatorio (entre $0.50 y $5.00)
            daily_cost = round(random.uniform(0.5, 5.0), 4)
            
            # Generar servicios con distribución realista
            services_data = []
            total_service_cost = 0
            
            for service in self.services[:random.randint(2, 5)]:  # 2-5 servicios por día
                service_cost = round(random.uniform(0.1, daily_cost * 0.8), 4)
                total_service_cost += service_cost
                services_data.append({
                    'Keys': [service],
                    'Metrics': {'BlendedCost': {'Amount': str(service_cost), 'Unit': 'USD'}}
                })
            
            # Ajustar para que sume el costo diario
            if services_data and total_service_cost < daily_cost:
                services_data[0]['Metrics']['BlendedCost']['Amount'] = str(
                    float(services_data[0]['Metrics']['BlendedCost']['Amount']) + 
                    (daily_cost - total_service_cost)
                )
            
            day_data = {
                'TimePeriod': {
                    'Start': current_date.strftime('%Y-%m-%d'),
                    'End': (current_date + timedelta(days=1)).strftime('%Y-%m-%d')
                },
                'Total': {'BlendedCost': {'Amount': str(daily_cost), 'Unit': 'USD'}},
                'Groups': services_data
            }
            
            mock_data['ResultsByTime'].append(day_data)
            current_date += timedelta(days=1)
        
        return mock_data
    
    def generate_ec2_instances(self):
        """Genera instancias EC2 ficticias para testing"""
        instance_types = [
            't2.micro', 't2.small', 't2.medium', 
            'm5.large', 'm5.xlarge', 'c5.large'
        ]
        
        instances = []
        for i in range(random.randint(3, 8)):
            instance_type = random.choice(instance_types)
            instances.append({
                'InstanceId': f'i-{random.randint(1000000000, 9999999999)}',
                'InstanceType': instance_type,
                'State': {'Name': 'running'},
                'LaunchTime': datetime.now() - timedelta(days=random.randint(1, 90))
            })
        
        return instances