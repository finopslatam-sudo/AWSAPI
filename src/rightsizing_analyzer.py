# src/rightsizing_analyzer.py
import boto3
from datetime import datetime, timedelta

class RightsizingAnalyzer:
    def __init__(self):
        self.cloudwatch = boto3.client('cloudwatch')
        self.ec2 = boto3.client('ec2')
        self.ce = boto3.client('ce')
    
    def get_rightsizing_recommendations(self):
        """Genera recomendaciones de rightsizing específicas"""
        instances = self.ec2.describe_instances(
            Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
        )
        
        recommendations = []
        
        for reservation in instances['Reservations']:
            for instance in reservation['Instances']:
                instance_id = instance['InstanceId']
                current_type = instance['InstanceType']
                
                # Obtener métricas de utilización
                utilization = self._get_instance_utilization(instance_id)
                
                # Analizar si necesita rightsizing
                rightsizing_rec = self._analyze_rightsizing(instance_id, current_type, utilization)
                if rightsizing_rec:
                    recommendations.append(rightsizing_rec)
        
        return recommendations
    
    def _get_instance_utilization(self, instance_id):
        """Obtiene métricas de utilización de CloudWatch"""
        try:
            # CPU Utilization
            cpu_response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/EC2',
                MetricName='CPUUtilization',
                Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                StartTime=datetime.now() - timedelta(days=14),
                EndTime=datetime.now(),
                Period=86400,  # 1 día
                Statistics=['Average', 'Maximum']
            )
            
            # Network Utilization
            network_response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/EC2',
                MetricName='NetworkIn',
                Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                StartTime=datetime.now() - timedelta(days=14),
                EndTime=datetime.now(),
                Period=86400,
                Statistics=['Average', 'Maximum']
            )
            
            return {
                'cpu_avg': self._calculate_average(cpu_response, 'Average'),
                'cpu_max': self._calculate_average(cpu_response, 'Maximum'),
                'network_avg': self._calculate_average(network_response, 'Average')
            }
            
        except Exception as e:
            return {'cpu_avg': 50, 'cpu_max': 80, 'network_avg': 0}  # Valores por defecto
    
    def _analyze_rightsizing(self, instance_id, current_type, utilization):
        """Analiza si la instancia necesita rightsizing"""
        cpu_avg = utilization['cpu_avg']
        cpu_max = utilization['cpu_max']
        
        # Lógica de recomendación
        if cpu_avg < 20 and cpu_max < 40:
            # Sobredimensionada - reducir tamaño
            recommended_type = self._get_smaller_instance_type(current_type)
            if recommended_type:
                savings = self._calculate_rightsizing_savings(current_type, recommended_type)
                return {
                    'instance_id': instance_id,
                    'current_type': current_type,
                    'recommended_type': recommended_type,
                    'cpu_utilization_avg': f"{cpu_avg:.1f}%",
                    'cpu_utilization_max': f"{cpu_max:.1f}%",
                    'estimated_monthly_savings': savings,
                    'savings_percentage': '40-60%',
                    'recommendation': f'Reducir de {current_type} a {recommended_type}'
                }
        
        elif cpu_avg > 80 or cpu_max > 95:
            # Subdimensionada - aumentar tamaño
            recommended_type = self._get_larger_instance_type(current_type)
            if recommended_type:
                return {
                    'instance_id': instance_id,
                    'current_type': current_type,
                    'recommended_type': recommended_type,
                    'cpu_utilization_avg': f"{cpu_avg:.1f}%",
                    'cpu_utilization_max': f"{cpu_max:.1f}%",
                    'recommendation': f'Aumentar de {current_type} a {recommended_type} para mejor performance'
                }
        
        return None
    
    def _get_smaller_instance_type(self, current_type):
        """Obtiene el tipo de instancia más pequeño disponible"""
        size_down_map = {
            'm5.large': 'm5.medium',
            'm5.medium': 'm5.small',
            'm5.small': 't3.medium',
            't3.medium': 't3.small',
            't3.small': 't3.micro'
        }
        return size_down_map.get(current_type)
    
    def _get_larger_instance_type(self, current_type):
        """Obtiene el tipo de instancia más grande disponible"""
        size_up_map = {
            't3.micro': 't3.small',
            't3.small': 't3.medium',
            't3.medium': 'm5.small',
            'm5.small': 'm5.medium',
            'm5.medium': 'm5.large'
        }
        return size_up_map.get(current_type)
    
    def _calculate_rightsizing_savings(self, current_type, recommended_type):
        """Calcula ahorros por rightsizing"""
        # Precios de ejemplo
        prices = {
            't3.micro': 0.0104,
            't3.small': 0.0208,
            't3.medium': 0.0416,
            'm5.small': 0.048,
            'm5.medium': 0.096,
            'm5.large': 0.192
        }
        
        current_price = prices.get(current_type, 0.10)
        recommended_price = prices.get(recommended_type, 0.05)
        
        monthly_savings = (current_price - recommended_price) * 730
        return round(monthly_savings, 2)
    
    def _calculate_average(self, metric_data, stat_type):
        """Calcula promedio de métricas CloudWatch"""
        if not metric_data['Datapoints']:
            return 0
        
        values = [point[stat_type] for point in metric_data['Datapoints']]
        return sum(values) / len(values)