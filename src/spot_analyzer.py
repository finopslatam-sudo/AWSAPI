# src/spot_analyzer.py
import boto3
from datetime import datetime, timedelta

class SpotAnalyzer:
    def __init__(self):
        self.ec2 = boto3.client('ec2')
        self.ce = boto3.client('ce')
    
    def get_spot_recommendations(self):
        """Genera recomendaciones específicas para Spot Instances"""
        # Analizar instancias actuales
        instances = self.ec2.describe_instances(
            Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
        )
        
        recommendations = []
        
        for reservation in instances['Reservations']:
            for instance in reservation['Instances']:
                instance_id = instance['InstanceId']
                instance_type = instance['InstanceType']
                
                # Verificar si es candidata para Spot
                if self._is_spot_candidate(instance):
                    savings_potential = self._calculate_spot_savings(instance_type)
                    
                    recommendations.append({
                        'instance_id': instance_id,
                        'instance_type': instance_type,
                        'current_lifecycle': 'on-demand',
                        'savings_potential': savings_potential,
                        'savings_percentage': '60-90%',
                        'risk_level': 'low',  # Basado en tipo de workload
                        'recommendation': f'Migrar {instance_id} a Spot Instance',
                        'estimated_monthly_savings': savings_potential
                    })
        
        return recommendations
    
    def _is_spot_candidate(self, instance):
        """Determina si una instancia es candidata para Spot"""
        # Lógica para identificar workloads adecuados para Spot
        # - Aplicaciones tolerantes a interrupciones
        # - Batch processing
        # - CI/CD pipelines
        # - Workloads flexibles
        
        # Por ahora, asumimos que todas las t3.micro son candidatas
        return instance['InstanceType'].startswith('t3.')
    
    def _calculate_spot_savings(self, instance_type):
        """Calcula ahorro potencial usando Spot Instances"""
        # Precios de ejemplo - en producción usarías Spot Price history
        spot_prices = {
            't3.micro': 0.003,
            't3.small': 0.006,
            'm5.large': 0.025
        }
        
        on_demand_prices = {
            't3.micro': 0.0104,
            't3.small': 0.0208,
            'm5.large': 0.096
        }
        
        spot_price = spot_prices.get(instance_type, 0.01)
        on_demand_price = on_demand_prices.get(instance_type, 0.05)
        
        monthly_savings = (on_demand_price - spot_price) * 730  # 730 horas/mes
        return round(monthly_savings, 2)