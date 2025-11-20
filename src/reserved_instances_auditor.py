import boto3
from typing import List, Dict
from datetime import datetime

class ReservedInstancesAuditor:
    """
    Auditor de Reserved Instances para identificar RIs subutilizadas
    """
    def __init__(self):
        self.ec2 = boto3.client('ec2')
        self.cloudwatch = boto3.client('cloudwatch')
    
    def get_ri_recommendations(self) -> List[Dict]:
        """Obtiene recomendaciones para optimizar Reserved Instances"""
        print("🔍 Analizando Reserved Instances...")
        
        # Obtener todas las RIs
        ris = self.ec2.describe_reserved_instances()
        recommendations = []
        
        for ri in ris['ReservedInstances']:
            if ri['State'] == 'active':
                utilization = self._calculate_ri_utilization(ri)
                
                if utilization < 70:  # RI subutilizada
                    recommendation = {
                        'ri_id': ri['ReservedInstancesId'],
                        'instance_type': ri['InstanceType'],
                        'current_utilization': utilization,
                        'savings_opportunity': self._calculate_savings_opportunity(ri, utilization),
                        'recommendation': self._generate_recommendation(utilization),
                        'risk_level': 'HIGH' if utilization < 50 else 'MEDIUM'
                    }
                    recommendations.append(recommendation)
        
        return recommendations
    
    def _calculate_ri_utilization(self, ri: Dict) -> float:
        """Calcula el porcentaje de utilización de una RI"""
        try:
            # Buscar instancias corriendo del mismo tipo
            instances = self.ec2.describe_instances(Filters=[
                {'Name': 'instance-type', 'Values': [ri['InstanceType']]},
                {'Name': 'instance-state-name', 'Values': ['running']}
            ])
            
            running_instances = sum(len(reservation['Instances']) for reservation in instances['Reservations'])
            ri_count = ri['InstanceCount']
            
            if ri_count > 0:
                return min((running_instances / ri_count) * 100, 100)
            return 0
        except Exception as e:
            print(f"Error calculando utilización de RI {ri['ReservedInstancesId']}: {e}")
            return 0
    
    def _calculate_savings_opportunity(self, ri: Dict, utilization: float) -> float:
        """Calcula ahorros potenciales por RI subutilizada"""
        # Estimación basada en costo mensual de la RI
        monthly_cost = self._estimate_monthly_ri_cost(ri)
        waste_percentage = (70 - utilization) / 100  # Asumiendo 70% como objetivo
        return monthly_cost * waste_percentage
    
    def _estimate_monthly_ri_cost(self, ri: Dict) -> float:
        """Estima el costo mensual de una RI"""
        if 'RecurringCharges' in ri and ri['RecurringCharges']:
            return float(ri['RecurringCharges'][0]['Amount']) * 730 / 24  # Convertir hora a mes
        return 100.0  # Valor por defecto si no hay información
    
    def _generate_recommendation(self, utilization: float) -> str:
        """Genera recomendación basada en el nivel de utilización"""
        if utilization < 30:
            return "Vender en RI Marketplace o terminar"
        elif utilization < 50:
            return "Reducir cantidad de instancias reservadas"
        elif utilization < 70:
            return "Modificar a tipo de instancia diferente"
        else:
            return "Optimización no requerida"