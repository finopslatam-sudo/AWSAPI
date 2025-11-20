from typing import Dict, List
from src.cur_analyzer import CURAnalyzer
from src.reserved_instances_auditor import ReservedInstancesAuditor
from src.spot_analyzer import SpotAnalyzer
from src.rightsizing_analyzer import RightsizingAnalyzer
from src.service_discovery import AWSServiceDiscovery
from datetime import datetime, timedelta

class FinOpsAuditor:
    """
    Auditor principal alineado con servicios de FinOps Latam
    """
    def __init__(self):
        self.service_discovery = AWSServiceDiscovery()
        self.cur_analyzer = CURAnalyzer()
        self.ri_auditor = ReservedInstancesAuditor()
        self.spot_analyzer = SpotAnalyzer()
        self.rightsizing_analyzer = RightsizingAnalyzer()
    
    def run_comprehensive_audit(self) -> Dict:
        """Ejecuta auditoría completa de FinOps Latam"""
        print("🔍 Iniciando Auditoría FinOps Latam...")
        
        # DESCUBRIMIENTO AUTOMÁTICO CON FILTRADO
        service_discovery = self.service_discovery.get_filtered_service_statistics()
        
        # Análisis tradicionales (solo para servicios detectados)
        cost_analysis = self.cur_analyzer.analyze_cost_drivers()
        ri_recommendations = self.ri_auditor.get_ri_recommendations()
        spot_recommendations = self.spot_analyzer.get_spot_recommendations()
        rightsizing_recommendations = self.rightsizing_analyzer.get_rightsizing_recommendations()
        
        audit_results = {
            'service_discovery': service_discovery,
            'cost_analysis': cost_analysis,
            'ri_recommendations': ri_recommendations,
            'spot_recommendations': spot_recommendations,
            'rightsizing_recommendations': rightsizing_recommendations,
            'executive_summary': self._generate_executive_summary(
                service_discovery,
                cost_analysis, 
                ri_recommendations, 
                spot_recommendations, 
                rightsizing_recommendations
            )
        }
        
        print("✅ Auditoría FinOps Latam completada")
        print(f"📊 Servicios en uso: {service_discovery['services_in_use']['total_services']}")
        print(f"🚫 Servicios no detectados: {service_discovery['services_not_detected']['total_services']}")
        
        return audit_results
    
    def _generate_executive_summary(self, service_discovery: Dict, cost_analysis: Dict, 
                                  ri_recommendations: List, spot_recommendations: List, 
                                  rightsizing_recommendations: List) -> Dict:
        """Genera resumen ejecutivo incluyendo descubrimiento de servicios"""
        total_savings = self._calculate_total_potential_savings(
            ri_recommendations, spot_recommendations, rightsizing_recommendations
        )
        
        current_monthly_cost = self._get_current_monthly_cost(cost_analysis)
        
        return {
            'infrastructure_overview': {
                'total_services': service_discovery['services_in_use']['total_services'],
                'total_resources': service_discovery['services_in_use']['total_resources'],
                'main_services': list(service_discovery['services_in_use']['breakdown'].keys())[:10]
            },
            'current_monthly_cost': current_monthly_cost,
            'total_potential_savings': total_savings,
            'savings_percentage': (total_savings / current_monthly_cost * 100) if current_monthly_cost > 0 else 0,
            'savings_breakdown': {
                'ri_optimization': sum(ri.get('savings_opportunity', 0) for ri in ri_recommendations),
                'spot_instances': sum(spot.get('monthly_savings', 0) for spot in spot_recommendations),
                'rightsizing': sum(rightsizing.get('estimated_savings', 0) for rightsizing in rightsizing_recommendations)
            },
            'recommendations_count': {
                'ri_optimization': len(ri_recommendations),
                'spot_instances': len(spot_recommendations),
                'rightsizing': len(rightsizing_recommendations)
            },
            'recommended_actions': self._generate_recommended_actions(
                ri_recommendations, spot_recommendations, rightsizing_recommendations
            ),
            'implementation_timeline': self._estimate_timeline(
                len(ri_recommendations), len(spot_recommendations), len(rightsizing_recommendations)
            ),
            'estimated_roi': self._calculate_roi(total_savings, current_monthly_cost),
            'risk_assessment': self._assess_implementation_risk(
                ri_recommendations, spot_recommendations, rightsizing_recommendations
            )
        }
    
    def _calculate_total_potential_savings(self, ri_recommendations: List, 
                                         spot_recommendations: List, 
                                         rightsizing_recommendations: List) -> float:
        """Calcula ahorros totales potenciales basados en todas las recomendaciones"""
        ri_savings = sum(ri.get('savings_opportunity', 0) for ri in ri_recommendations)
        spot_savings = sum(spot.get('monthly_savings', 0) for spot in spot_recommendations)
        rightsizing_savings = sum(rightsizing.get('estimated_savings', 0) for rightsizing in rightsizing_recommendations)
        
        return ri_savings + spot_savings + rightsizing_savings
    
    def _get_current_monthly_cost(self, cost_analysis: Dict) -> float:
        """Obtiene el costo mensual actual del análisis de costos"""
        try:
            if 'top_services' in cost_analysis and cost_analysis['top_services']:
                total_cost = sum(service.get('cost', 0) for service in cost_analysis['top_services'])
                return total_cost
        except Exception as e:
            print(f"⚠️  No se pudo obtener costo mensual: {e}")
        
        # Valor por defecto si no se puede calcular
        return 5000.0
    
    def _generate_recommended_actions(self, ri_recommendations: List, 
                                    spot_recommendations: List, 
                                    rightsizing_recommendations: List) -> List[str]:
        """Genera lista de acciones recomendadas basadas en los hallazgos"""
        actions = []
        
        # Acciones para RIs
        if ri_recommendations:
            high_risk_ris = [ri for ri in ri_recommendations if ri.get('risk_level') == 'HIGH']
            if high_risk_ris:
                actions.append(f"Optimizar {len(high_risk_ris)} Reserved Instances críticamente subutilizadas")
            actions.append(f"Revisar {len(ri_recommendations)} Reserved Instances para mejorar utilización")
        
        # Acciones para Spot Instances
        if spot_recommendations:
            high_savings_spot = [spot for spot in spot_recommendations if spot.get('savings_percentage', 0) > 60]
            if high_savings_spot:
                actions.append(f"Implementar {len(high_savings_spot)} Spot Instances con ahorros >60%")
            actions.append(f"Evaluar {len(spot_recommendations)} oportunidades de Spot Instances")
        
        # Acciones para Rightsizing
        if rightsizing_recommendations:
            downsizing_ops = [rs for rs in rightsizing_recommendations if rs.get('recommendation') != 'UPGRADE']
            if downsizing_ops:
                actions.append(f"Redimensionar {len(downsizing_ops)} instancias sobredimensionadas")
            actions.append(f"Optimizar configuración de {len(rightsizing_recommendations)} recursos")
        
        # Acciones generales
        actions.append("Establecer monitoreo continuo de costos y utilización")
        actions.append("Implementar alertas de presupuesto y anomalías")
        actions.append("Crear procesos de revisión mensual de costos")
        
        return actions
    
    def _estimate_timeline(self, ri_count: int, spot_count: int, rightsizing_count: int) -> str:
        """Estima el timeline de implementación basado en la complejidad"""
        total_recommendations = ri_count + spot_count + rightsizing_count
        
        if total_recommendations == 0:
            return "No se requieren acciones inmediatas"
        elif total_recommendations <= 5:
            return "2-3 semanas"
        elif total_recommendations <= 15:
            return "4-6 semanas"
        else:
            return "6-8 semanas"
    
    def _calculate_roi(self, potential_savings: float, current_cost: float) -> str:
        """Calcula el ROI estimado"""
        if current_cost == 0:
            return "N/A"
        
        annual_savings = potential_savings * 12
        implementation_cost = current_cost * 0.1  # Estimación del 10% del costo mensual para implementación
        
        if implementation_cost == 0:
            return "∞"
        
        roi_percentage = (annual_savings / implementation_cost) * 100
        
        if roi_percentage > 500:
            return ">500% en el primer año"
        elif roi_percentage > 200:
            return ">200% en el primer año"
        elif roi_percentage > 100:
            return ">100% en el primer año"
        else:
            return f"{roi_percentage:.0f}% en el primer año"
    
    def _assess_implementation_risk(self, ri_recommendations: List, 
                                  spot_recommendations: List, 
                                  rightsizing_recommendations: List) -> Dict:
        """Evalúa el riesgo de implementación de las recomendaciones"""
        high_risk_count = 0
        medium_risk_count = 0
        low_risk_count = 0
        
        # Evaluar riesgos de RIs
        for ri in ri_recommendations:
            if ri.get('risk_level') == 'HIGH':
                high_risk_count += 1
            else:
                medium_risk_count += 1
        
        # Evaluar riesgos de Spot (generalmente medio riesgo)
        medium_risk_count += len(spot_recommendations)
        
        # Evaluar riesgos de Rightsizing (generalmente bajo riesgo)
        low_risk_count += len([rs for rs in rightsizing_recommendations if rs.get('recommendation') != 'UPGRADE'])
        medium_risk_count += len([rs for rs in rightsizing_recommendations if rs.get('recommendation') == 'UPGRADE'])
        
        total_risks = high_risk_count + medium_risk_count + low_risk_count
        
        if total_risks == 0:
            return {'level': 'LOW', 'description': 'Sin riesgos identificados'}
        
        high_risk_percentage = (high_risk_count / total_risks) * 100
        
        if high_risk_percentage > 30:
            return {'level': 'HIGH', 'description': 'Se recomienda implementación gradual'}
        elif high_risk_percentage > 15:
            return {'level': 'MEDIUM', 'description': 'Riesgo moderado, planificar cuidadosamente'}
        else:
            return {'level': 'LOW', 'description': 'Riesgo bajo, se puede implementar agresivamente'}

# Para uso directo del módulo
if __name__ == "__main__":
    auditor = FinOpsAuditor()
    results = auditor.run_comprehensive_audit()
    print("🔍 Auditoría completada. Resumen ejecutivo:")
    print(f"💰 Ahorros potenciales: ${results['executive_summary']['total_potential_savings']:,.2f} USD")