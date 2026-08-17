from src.models.azure_resource_inventory import AzureResourceInventory
from src.models.azure_finding import AzureFinding


class CosmosDBRules:

    @staticmethod
    def run_all(client_id: int):
        total = 0
        total += CosmosDBRules.public_network_access_rule(client_id)
        total += CosmosDBRules.multi_region_review_rule(client_id)
        return total

    # =====================================================
    # ACCESO DE RED PÚBLICO SIN FILTRO DE VNET
    # =====================================================
    @staticmethod
    def public_network_access_rule(client_id: int):

        return CosmosDBRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get("public_network_access") == "Enabled"
            and not (r.resource_metadata or {}).get("is_virtual_network_filter_enabled"),
            finding_type="COSMOSDB_PUBLIC_NETWORK_ACCESS",
            severity="HIGH",
            message="Cuenta Cosmos DB con acceso de red público habilitado y sin filtro de VNet; restringir con Private Endpoint o reglas de firewall de IP.",
            savings=0,
        )

    # =====================================================
    # REPLICACIÓN MULTI-REGIÓN (MULTIPLICA EL COSTO)
    # =====================================================
    # Cada región adicional en una cuenta Cosmos DB multiplica el costo
    # de throughput y almacenamiento — es el driver de costo #1 en
    # Cosmos DB, sin equivalente exacto en el resto del catálogo ya
    # cubierto (RDS Multi-AZ es distinto: solo duplica, no reproduce
    # el mismo patrón de "una copia completa por región agregada").
    @staticmethod
    def multi_region_review_rule(client_id: int):

        return CosmosDBRules._evaluate_rule(
            client_id,
            condition=lambda r: ((r.resource_metadata or {}).get("region_count") or 0) > 1,
            finding_type="COSMOSDB_MULTI_REGION_REVIEW",
            severity="MEDIUM",
            message="Cuenta Cosmos DB replicada en múltiples regiones; cada región adicional multiplica el costo de throughput y almacenamiento. Verificar si la redundancia geográfica es realmente necesaria.",
            savings=0,
        )

    # =====================================================
    # CORE ENGINE (IDEMPOTENTE, CON AUTO-RESOLUCIÓN)
    # =====================================================
    @staticmethod
    def _evaluate_rule(client_id, condition, finding_type, severity, message, savings):

        resources = AzureResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="CosmosDB",
            resource_type="DatabaseAccount",
            is_active=True
        ).all()

        findings_created = 0

        for resource in resources:

            existing = AzureFinding.query.filter_by(
                client_id=client_id,
                resource_id=resource.resource_id,
                finding_type=finding_type
            ).first()

            if condition(resource):

                if existing:
                    existing.resolved = False
                    existing.message = message
                    existing.severity = severity
                    existing.estimated_monthly_savings = savings
                else:
                    created = AzureFinding.upsert_finding(
                        client_id=client_id,
                        azure_account_id=resource.azure_account_id,
                        resource_id=resource.resource_id,
                        resource_type=resource.resource_type,
                        region=resource.region,
                        azure_service="CosmosDB",
                        finding_type=finding_type,
                        severity=severity,
                        message=message,
                        estimated_monthly_savings=savings
                    )
                    if created:
                        findings_created += 1

            else:
                if existing and not existing.resolved:
                    existing.resolved = True

        return findings_created
