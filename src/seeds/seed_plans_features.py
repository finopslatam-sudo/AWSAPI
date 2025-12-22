from app import app
from src.auth_system import db, Plan, Feature, PlanFeature

def seed_plans_and_features():
    with app.app_context():

        # -------------------
        # LIMPIEZA (idempotente)
        # -------------------
        db.session.query(PlanFeature).delete()
        db.session.query(Feature).delete()
        db.session.query(Plan).delete()
        db.session.commit()

        # -------------------
        # FEATURES BASE
        # -------------------
        features = {
            # Assessment
            "inventory": "Inventario completo de recursos cloud",
            "unused_resources": "Detección de recursos no utilizados",
            "cost_by_service": "Costos por servicio/proyecto",
            "quick_wins": "Identificación de quick wins",
            "basic_dashboard": "Dashboard básico de visibilidad",

            # Intelligence
            "real_time_dashboards": "Dashboards en tiempo real",
            "budget_alerts": "Alertas de gasto y budgets",
            "forecasting": "Forecasting de costos",
            "cost_allocation": "Cost allocation por tags/departamentos",
            "anomaly_detection": "Detección automática de anomalías",

            # FinOps
            "ri_analysis": "Análisis de Reserved Instances",
            "savings_plans": "Optimización de Savings Plans",
            "roi_analysis": "Análisis de ROI cloud",
            "spot_strategy": "Estrategia Spot Instances",

            # Optimization
            "rightsizing": "Right-sizing automatizado",
            "autoscaling": "Auto-scaling inteligente",
            "storage_optimization": "Optimización de storage",
            "container_optimization": "Optimización de contenedores",
            "automation_actions": "Acciones automáticas de ahorro",

            # Governance
            "tagging_strategy": "Estrategia de tagging",
            "budgets_guardrails": "Budgets y guardrails",
            "policy_as_code": "Policy as Code (Terraform)",
            "finops_training": "Entrenamiento FinOps",
            "operating_model": "Modelo operativo FinOps"
        }

        feature_objs = {}
        for code, desc in features.items():
            f = Feature(code=code, description=desc)
            db.session.add(f)
            feature_objs[code] = f

        db.session.commit()

        # -------------------
        # PLANES (jerárquicos)
        # -------------------
        plans = [
            ("assessment", "Cloud Assessment", 499, [
                "inventory", "unused_resources", "cost_by_service",
                "quick_wins", "basic_dashboard"
            ]),
            ("intelligence", "Cloud Intelligence", 999, [
                "real_time_dashboards", "budget_alerts",
                "forecasting", "cost_allocation", "anomaly_detection"
            ]),
            ("finops", "Cloud Financial Operations", 1499, [
                "ri_analysis", "savings_plans",
                "roi_analysis", "spot_strategy"
            ]),
            ("optimization", "Cloud Optimization", 1999, [
                "rightsizing", "autoscaling",
                "storage_optimization", "container_optimization",
                "automation_actions"
            ]),
            ("governance", "Cloud Governance", 2499, [
                "tagging_strategy", "budgets_guardrails",
                "policy_as_code", "finops_training",
                "operating_model"
            ])
        ]

        previous_features = []

        for code, name, price, feature_codes in plans:
            plan = Plan(
                code=code,
                name=name,
                monthly_price=price,
                is_active=True
            )
            db.session.add(plan)
            db.session.flush()

            # Jerarquía acumulativa
            all_features = previous_features + feature_codes

            for f_code in all_features:
                db.session.add(
                    PlanFeature(
                        plan_id=plan.id,
                        feature_id=feature_objs[f_code].id
                    )
                )

            previous_features = all_features

        db.session.commit()
        print("✅ Planes y features cargados correctamente")

if __name__ == "__main__":
    seed_plans_and_features()
