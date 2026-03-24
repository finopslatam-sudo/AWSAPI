from sqlalchemy import func, and_
from src.models.aws_finding import AWSFinding
from src.models.aws_resource_inventory import AWSResourceInventory
from src.models.aws_account import AWSAccount
from src.models.database import db
from src.services.dashboard.risk_service import RiskService
from src.services.dashboard.governance_service import GovernanceService
from src.services.dashboard.roi_service import ROIService


class ExecutiveService:

    # =====================================================
    # EXECUTIVE SUMMARY ENGINE (ENTERPRISE READY)
    # =====================================================
    @staticmethod
    def get_executive_summary(
        client_id: int,
        aws_account_id: int | None = None,
        risk: dict | None = None,
        governance: dict | None = None,
        roi: dict | None = None,
        priority_services: list | None = None,
    ):

        # -----------------------------------------------------
        # CORE METRICS
        # -----------------------------------------------------
        if risk is None:
            risk = RiskService.get_risk_score(client_id, aws_account_id)

        if governance is None:
            governance = GovernanceService.get_governance_score(
                client_id,
                aws_account_id
            )

        if roi is None:
            roi = ROIService.get_roi_projection(client_id, aws_account_id)

        if priority_services is None:
            priority_services = RiskService.get_priority_services(
                client_id,
                aws_account_id
            )

        # -----------------------------------------------------
        # PRIMARY RISK DRIVER
        # -----------------------------------------------------
        primary_service = (
            priority_services[0]["service"]
            if priority_services else None
        )

        # -----------------------------------------------------
        # FINANCIAL EXPOSURE (ACTIVE FINDINGS ONLY + INVENTORY ACTIVE)
        # -----------------------------------------------------
        monthly_exposure_query = (
            db.session.query(
                func.sum(AWSFinding.estimated_monthly_savings)
            )
            .join(
                AWSResourceInventory,
                and_(
                    AWSFinding.resource_id == AWSResourceInventory.resource_id,
                    AWSFinding.client_id == AWSResourceInventory.client_id
                )
            )
            .filter(
                AWSFinding.client_id == client_id,
                AWSFinding.resolved.is_(False),
                AWSResourceInventory.is_active.is_(True)
            )
        )

        if aws_account_id is not None:
            monthly_exposure_query = monthly_exposure_query.filter(
                AWSFinding.aws_account_id == aws_account_id,
                AWSResourceInventory.aws_account_id == aws_account_id
            )

        monthly_exposure = monthly_exposure_query.scalar() or 0

        monthly_exposure = float(monthly_exposure)
        annual_exposure = round(monthly_exposure * 12, 2)

        # -----------------------------------------------------
        # GOVERNANCE STATUS CLASSIFICATION
        # -----------------------------------------------------
        compliance = governance["compliance_percentage"]

        if compliance >= 95:
            governance_status = "EXCELLENT"
        elif compliance >= 85:
            governance_status = "GOOD"
        elif compliance >= 70:
            governance_status = "FAIR"
        else:
            governance_status = "POOR"

        # -----------------------------------------------------
        # URGENCY LEVEL (BASED ON RISK)
        # -----------------------------------------------------
        urgency_level = ExecutiveService._calculate_urgency(
            risk["risk_level"]
        )

        # -----------------------------------------------------
        # ACCOUNT FOOTPRINT
        # -----------------------------------------------------
        accounts_query = AWSAccount.query.filter_by(
            client_id=client_id,
            is_active=True
        )

        if aws_account_id is not None:
            accounts_query = accounts_query.filter(
                AWSAccount.id == aws_account_id
            )

        accounts_count = accounts_query.count()

        # -----------------------------------------------------
        # NARRATIVE GENERATION
        # -----------------------------------------------------
        narrative = ExecutiveService._build_narrative(
            risk_level=risk["risk_level"],
            risk_score=risk["risk_score"],
            governance_status=governance_status,
            primary_service=primary_service,
            monthly_exposure=monthly_exposure,
            annual_exposure=annual_exposure,
            accounts_count=accounts_count,
            projected_risk_score=roi["projected_risk_score"]
        )

        return {
            "overall_posture": ExecutiveService._translate_risk_level(
                risk["risk_level"]
            ),
            "risk_score": risk["risk_score"],
            "urgency_level": urgency_level,
            "primary_risk_driver": primary_service,
            "governance_status": ExecutiveService._translate_governance_status(
                governance_status
            ),
            "governance_score": compliance,
            "monthly_financial_exposure": round(monthly_exposure, 2),
            "annual_financial_exposure": annual_exposure,
            "projected_risk_score_after_high_remediation": roi["projected_risk_score"],
            "accounts_covered": accounts_count,
            "message": narrative
        }

    # =====================================================
    # INTERNAL: URGENCY CALCULATOR
    # =====================================================
    @staticmethod
    def _calculate_urgency(risk_level: str):

        mapping = {
            "LOW": "MONITOREAR",
            "MODERATE": "ATENCION_REQUERIDA",
            "HIGH": "ACCION_PRIORITARIA",
            "CRITICAL": "ACCION_INMEDIATA"
        }

        return mapping.get(risk_level, "MONITOREAR")

    @staticmethod
    def _translate_risk_level(risk_level: str):

        mapping = {
            "LOW": "BAJO",
            "MODERATE": "MODERADO",
            "HIGH": "ALTO",
            "CRITICAL": "CRITICO"
        }

        return mapping.get(risk_level, risk_level)

    @staticmethod
    def _translate_governance_status(governance_status: str):

        mapping = {
            "EXCELLENT": "EXCELENTE",
            "GOOD": "BUENO",
            "FAIR": "ACEPTABLE",
            "POOR": "DEFICIENTE"
        }

        return mapping.get(governance_status, governance_status)

    # =====================================================
    # INTERNAL: EXECUTIVE NARRATIVE BUILDER
    # =====================================================
    @staticmethod
    def _build_narrative(
        risk_level,
        risk_score,
        governance_status,
        primary_service,
        monthly_exposure,
        annual_exposure,
        accounts_count,
        projected_risk_score
    ):

        risk_level_es = ExecutiveService._translate_risk_level(risk_level)
        governance_status_es = (
            ExecutiveService._translate_governance_status(governance_status)
        )
        account_label = (
            "cuenta conectada"
            if accounts_count == 1 else
            "cuentas conectadas"
        )

        message = (
            f"La organizacion opera actualmente con una postura de riesgo "
            f"{risk_level_es} (score: {risk_score}) en "
            f"{accounts_count} {account_label}. "
        )

        message += (
            f"La madurez de gobernanza se clasifica como "
            f"{governance_status_es}. "
        )

        if primary_service:
            message += (
                f"El principal generador de riesgo es {primary_service}, "
                f"por lo que deberia priorizarse para remediacion. "
            )

        if monthly_exposure > 0:
            message += (
                f"La exposicion financiera estimada es de "
                f"${round(monthly_exposure, 2)} mensuales "
                f"(${annual_exposure} anuales). "
            )

            message += (
                f"La remediacion de los hallazgos de severidad alta, por si sola, "
                f"mejoraria el score de riesgo a aproximadamente "
                f"{projected_risk_score}. "
            )
        else:
            message += (
                "No se ha identificado una exposicion financiera inmediata significativa. "
            )

        return message.strip()
