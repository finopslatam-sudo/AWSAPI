import boto3
from typing import Dict, List, Set, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

class AWSServiceDiscovery:
    """
    Descubre automáticamente todos los servicios AWS en uso
    y filtra los no utilizados
    """
    def __init__(self):
        self.session = boto3.Session()
        self.available_services = self.session.get_available_services()
        # Servicios que siempre verificamos (críticos para FinOps)
        self.high_priority_services = [
            'ec2', 'rds', 's3', 'lambda', 'dynamodb', 'elasticache', 
            'eks', 'ecs', 'redshift', 'cloudfront'
        ]
    
    def discover_services_with_filtering(self) -> Tuple[Dict, List, List]:
        """
        Descubre servicios y retorna:
        - servicios_en_uso: Dict con recursos
        - servicios_no_detectados: List de servicios sin recursos
        - servicios_con_error: List de servicios con errores
        """
        print("🔍 Descubriendo y filtrando servicios AWS...")
        
        servicios_en_uso = {}
        servicios_no_detectados = []
        servicios_con_error = []
        
        # Verificar servicios en paralelo
        with ThreadPoolExecutor(max_workers=15) as executor:
            future_to_service = {
                executor.submit(self._check_service_usage, service): service 
                for service in self.available_services
            }
            
            for future in as_completed(future_to_service):
                service = future_to_service[future]
                try:
                    result = future.result()
                    
                    if result['has_resources']:
                        servicios_en_uso[service] = result
                        print(f"✅ {service}: {len(result['resources'])} recursos")
                    else:
                        # Solo mostrar servicios de alta prioridad aunque estén vacíos
                        if service in self.high_priority_services:
                            servicios_en_uso[service] = result
                            print(f"ℹ️  {service}: Sin recursos (servicio crítico)")
                        else:
                            servicios_no_detectados.append(service)
                            
                except Exception as e:
                    servicios_con_error.append({
                        'service': service,
                        'error': str(e)
                    })
                    print(f"❌ {service}: Error en descubrimiento")
        
        return servicios_en_uso, servicios_no_detectados, servicios_con_error
    
    def get_filtered_service_statistics(self) -> Dict:
        """Obtiene estadísticas filtradas de servicios en uso"""
        servicios_en_uso, servicios_no_detectados, servicios_con_error = self.discover_services_with_filtering()
        
        total_resources = sum(len(details['resources']) for details in servicios_en_uso.values())
        
        # Calcular porcentaje de cobertura
        total_services_checked = len(servicios_en_uso) + len(servicios_no_detectados)
        coverage_percentage = (len(servicios_en_uso) / total_services_checked * 100) if total_services_checked > 0 else 0
        
        return {
            'services_in_use': {
                'total_services': len(servicios_en_uso),
                'total_resources': total_resources,
                'coverage_percentage': round(coverage_percentage, 1),
                'breakdown': {
                    service: {
                        'resource_count': len(details['resources']),
                        'resources': details['resources'][:10],  # Máximo 10 recursos por servicio
                        'last_checked': datetime.now().isoformat()
                    }
                    for service, details in servicios_en_uso.items()
                }
            },
            'services_not_detected': {
                'total_services': len(servicios_no_detectados),
                'services': servicios_no_detectados[:50],  # Top 50 servicios no detectados
                'note': 'Estos servicios no tienen recursos activos en la cuenta actual'
            },
            'services_with_errors': {
                'total_services': len(servicios_con_error),
                'services': servicios_con_error[:20]  # Top 20 servicios con errores
            },
            'discovery_metadata': {
                'timestamp': datetime.now().isoformat(),
                'total_services_available': len(self.available_services),
                'high_priority_services': self.high_priority_services
            }
        }
    
    def _check_service_usage(self, service_name: str) -> Dict:
        """Verifica si un servicio específico está en uso (versión mejorada)"""
        try:
            client = self.session.client(service_name)
            resources = []
            
            # DETECCIÓN PARA SERVICIOS COMUNES
            if service_name == 'ec2':
                instances = client.describe_instances()
                for reservation in instances['Reservations']:
                    for instance in reservation['Instances']:
                        if instance['State']['Name'] == 'running':  # Solo instancias running
                            resources.append({
                                'type': 'EC2 Instance',
                                'id': instance['InstanceId'],
                                'state': instance['State']['Name'],
                                'instance_type': instance.get('InstanceType', 'N/A'),
                                'launch_time': instance.get('LaunchTime').isoformat() if instance.get('LaunchTime') else 'N/A'
                            })
            
            elif service_name == 's3':
                buckets = client.list_buckets()
                for bucket in buckets['Buckets']:
                    resources.append({
                        'type': 'S3 Bucket',
                        'name': bucket['Name'],
                        'creation_date': bucket['CreationDate'].isoformat()
                    })
            
            elif service_name == 'rds':
                instances = client.describe_db_instances()
                for instance in instances['DBInstances']:
                    resources.append({
                        'type': 'RDS Instance',
                        'id': instance['DBInstanceIdentifier'],
                        'engine': instance['Engine'],
                        'status': instance['DBInstanceStatus'],
                        'instance_class': instance.get('DBInstanceClass', 'N/A')
                    })
            
            elif service_name == 'lambda':
                functions = client.list_functions()
                for function in functions['Functions']:
                    resources.append({
                        'type': 'Lambda Function',
                        'name': function['FunctionName'],
                        'runtime': function['Runtime'],
                        'last_modified': function['LastModified']
                    })
            
            elif service_name == 'dynamodb':
                tables = client.list_tables()
                for table_name in tables['TableNames']:
                    resources.append({
                        'type': 'DynamoDB Table',
                        'name': table_name
                    })
            
            elif service_name == 'cloudwatch':
                # Solo alarms activas
                alarms = client.describe_alarms(StateValue='ALARM')
                for alarm in alarms['MetricAlarms']:
                    resources.append({
                        'type': 'CloudWatch Alarm',
                        'name': alarm['AlarmName'],
                        'state': alarm['StateValue']
                    })
            
            # Agregar más servicios según necesites
            # ... (el resto de las detecciones que ya tenías)
            
            return {
                'has_resources': len(resources) > 0,
                'resources': resources,
                'resource_count': len(resources),
                'service_name': service_name
            }
            
        except Exception as e:
            return {
                'has_resources': False,
                'resources': [],
                'resource_count': 0,
                'error': str(e),
                'service_name': service_name
            }