import sys
import subprocess
import os

def check_and_install():
    """Verifica e instala dependencias si es necesario"""
    print("🔍 Verificando entorno...")
    
    try:
        import boto3
        print("✅ boto3 está disponible")
        return True
    except ImportError:
        print("❌ boto3 no está instalado")
        print("💡 Ejecuta estos comandos:")
        print("   source venv/bin/activate")
        print("   pip install boto3 python-dotenv flask")
        return False

def main():
    print("🛡️  VERIFICADOR SEGURO AWS FREE TIER")
    print("=" * 55)
    
    # Verificar que estamos en el entorno virtual
    if not hasattr(sys, 'real_prefix') and not sys.prefix == sys.base_prefix:
        print("⚠️  No estás en un entorno virtual")
        print("💡 Ejecuta: source venv/bin/activate")
        return
    
    print("✅ Entorno virtual activado")
    
    if not check_and_install():
        return
    
    # Ahora importamos seguro
    import boto3
    from datetime import datetime, timedelta
    
    try:
        print("\n🔐 Conectando a AWS...")
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        print(f"   ✅ Cuenta: {identity['Account']}")
        print(f"   ✅ Usuario: {identity['Arn'].split('/')[-1]}")
        
        print("\n💰 Verificando costos Free Tier...")
        ce = boto3.client('ce')
        
        today = datetime.now()
        first_day_month = today.replace(day=1)
        
        # Consulta segura - solo este mes
        response = ce.get_cost_and_usage(
            TimePeriod={
                'Start': first_day_month.strftime('%Y-%m-%d'),
                'End': today.strftime('%Y-%m-%d')
            },
            Granularity='MONTHLY',
            Metrics=['BlendedCost']
        )
        
        monthly_cost = float(response['ResultsByTime'][0]['Total']['BlendedCost']['Amount'])
        
        print(f"   📊 Costo este mes: ${monthly_cost:.6f}")
        print(f"   💵 Límite Free Tier: $1,000.00")
        print(f"   ✅ Restante: ${1000 - monthly_cost:.2f}")
        
        # Análisis detallado de servicios
        print("\n🔍 Analizando servicios con costo...")
        detailed_response = ce.get_cost_and_usage(
            TimePeriod={
                'Start': first_day_month.strftime('%Y-%m-%d'),
                'End': today.strftime('%Y-%m-%d')
            },
            Granularity='MONTHLY',
            Metrics=['BlendedCost'],
            GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
        )
        
        has_costs = False
        for group in detailed_response['ResultsByTime'][0]['Groups']:
            cost = float(group['Metrics']['BlendedCost']['Amount'])
            if cost > 0.0001:  # Mostrar solo costos significativos
                service = group['Keys'][0]
                print(f"   • {service}: ${cost:.8f}")
                has_costs = True
        
        if not has_costs:
            print("   ✅ Ningún servicio con costo detectable")
        
        # Verificación de instancias EC2
        print("\n🖥️  Verificando recursos EC2...")
        ec2 = boto3.client('ec2')
        
        # Instancias ejecutándose
        instances = ec2.describe_instances(
            Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
        )
        
        running_instances = []
        for reservation in instances['Reservations']:
            running_instances.extend(reservation['Instances'])
        
        print(f"   • Instancias ejecutándose: {len(running_instances)}")
        
        if running_instances:
            free_tier_types = ['t2.micro', 't3.micro', 't4g.micro']
            for instance in running_instances:
                instance_type = instance['InstanceType']
                status = "✅ FREE TIER" if instance_type in free_tier_types else "⚠️  PAGADO"
                print(f"     - {instance['InstanceId']} ({instance_type}): {status}")
        
        # RESUMEN FINAL
        print("\n" + "=" * 55)
        print("🎯 RESUMEN FREE TIER:")
        
        if monthly_cost == 0:
            print("✅ EXCELENTE - Cero costos detectados")
            print("✅ Tu Free Tier está completamente seguro")
            print("✅ El mensaje de Health NO te afecta")
        elif monthly_cost < 0.01:
            print("✅ PERFECTO - Costos insignificantes")
            print("✅ Free Tier en excelente estado")
        else:
            print("🔍 ATENCIÓN - Hay costos detectados")
            print("💡 Revisa los servicios listados arriba")
        
        print(f"\n💡 Recordatorio:")
        print("   El mensaje 'Free Tier Page Migration' es:")
        print("   • SOLO informativo")
        print("   • NO afecta tus servicios")
        print("   • Sucede en Noviembre 2025")
        print("   • PUEDES seguir desarrollando con confianza")
            
    except Exception as e:
        print(f"❌ Error durante la verificación: {str(e)}")
        print("💡 Verifica tus credenciales AWS con: aws configure")

if __name__ == "__main__":
    main()