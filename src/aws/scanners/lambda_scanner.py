import logging

from src.aws.scanners.shared import BaseScanner


logger = logging.getLogger(__name__)


class LambdaScanner(BaseScanner):
    """Handles Lambda functions, CloudWatch Log Groups, ECS, and EKS."""

    # ------------------------------------------------------------------
    # LAMBDA
    # ------------------------------------------------------------------
    def scan_lambda(self, region):
        try:
            lambda_client = self.aws_session.client("lambda", region_name=region)
            paginator = lambda_client.get_paginator("list_functions")

            for page in paginator.paginate():
                for function in page.get("Functions", []):
                    self.upsert_resource(
                        service_name="Lambda",
                        resource_type="Function",
                        resource_id=function["FunctionName"],
                        region=region,
                        state="active",
                        tags={},
                        resource_metadata={
                            "runtime": function.get("Runtime"),
                            "handler": function.get("Handler"),
                            "memory_size": function.get("MemorySize"),
                            "timeout": function.get("Timeout"),
                            "last_modified": function.get("LastModified"),
                        }
                    )

        except Exception:
            logger.exception(f"Lambda scan failed | region={region}")
            raise

    # ------------------------------------------------------------------
    # CLOUDWATCH LOGS
    # ------------------------------------------------------------------
    def scan_cloudwatch_logs(self, region):
        try:
            logs_client = self.aws_session.client("logs", region_name=region)
            paginator = logs_client.get_paginator("describe_log_groups")

            for page in paginator.paginate():
                for log_group in page.get("logGroups", []):
                    self.upsert_resource(
                        service_name="CloudWatch",
                        resource_type="LogGroup",
                        resource_id=log_group["logGroupName"],
                        region=region,
                        state="active",
                        tags={},
                        resource_metadata={
                            "stored_bytes": log_group.get("storedBytes"),
                            "retention_days": log_group.get("retentionInDays"),
                            "creation_time": log_group.get("creationTime"),
                        }
                    )

        except Exception:
            logger.exception(f"CloudWatch Logs scan failed | region={region}")
            raise

    # ------------------------------------------------------------------
    # ECS
    # ------------------------------------------------------------------
    def scan_ecs(self, region):
        try:
            ecs = self.aws_session.client("ecs", region_name=region)

            cluster_arns = ecs.list_clusters().get("clusterArns", [])

            for cluster_arn in cluster_arns:
                cluster_details = ecs.describe_clusters(
                    clusters=[cluster_arn]
                )["clusters"][0]

                cluster_name = cluster_details.get("clusterName")

                self.upsert_resource(
                    service_name="ECS",
                    resource_type="Cluster",
                    resource_id=cluster_name,
                    region=region,
                    state="active",
                    tags={},
                    resource_metadata={
                        "status": cluster_details.get("status"),
                        "running_tasks": cluster_details.get("runningTasksCount"),
                        "pending_tasks": cluster_details.get("pendingTasksCount"),
                        "active_services": cluster_details.get("activeServicesCount"),
                    }
                )

                service_arns = ecs.list_services(
                    cluster=cluster_arn
                ).get("serviceArns", [])

                if service_arns:
                    services = ecs.describe_services(
                        cluster=cluster_arn,
                        services=service_arns
                    )["services"]

                    for service in services:
                        self.upsert_resource(
                            service_name="ECS",
                            resource_type="Service",
                            resource_id=service.get("serviceName"),
                            region=region,
                            state=service.get("status"),
                            tags={},
                            resource_metadata={
                                "desired_count": service.get("desiredCount"),
                                "running_count": service.get("runningCount"),
                                "pending_count": service.get("pendingCount"),
                                "launch_type": service.get("launchType"),
                                "task_definition": service.get("taskDefinition"),
                                "cluster_arn": cluster_arn,
                            }
                        )

        except Exception:
            logger.exception(f"ECS scan failed | region={region}")
            raise

    # ------------------------------------------------------------------
    # EKS
    # ------------------------------------------------------------------
    def scan_eks(self, region):
        try:
            eks = self.aws_session.client("eks", region_name=region)

            cluster_names = eks.list_clusters().get("clusters", [])

            for cluster_name in cluster_names:
                cluster = eks.describe_cluster(name=cluster_name)["cluster"]

                self.upsert_resource(
                    service_name="EKS",
                    resource_type="Cluster",
                    resource_id=cluster_name,
                    region=region,
                    state=cluster.get("status"),
                    tags={},
                    resource_metadata={
                        "version": cluster.get("version"),
                        "endpoint": cluster.get("endpoint"),
                        "platform_version": cluster.get("platformVersion"),
                    }
                )

                nodegroups = eks.list_nodegroups(
                    clusterName=cluster_name
                ).get("nodegroups", [])

                for nodegroup_name in nodegroups:
                    nodegroup = eks.describe_nodegroup(
                        clusterName=cluster_name,
                        nodegroupName=nodegroup_name
                    )["nodegroup"]

                    self.upsert_resource(
                        service_name="EKS",
                        resource_type="NodeGroup",
                        resource_id=nodegroup_name,
                        region=region,
                        state=nodegroup.get("status"),
                        tags={},
                        resource_metadata={
                            "instance_types": nodegroup.get("instanceTypes"),
                            "min_size": nodegroup.get("scalingConfig", {}).get("minSize"),
                            "max_size": nodegroup.get("scalingConfig", {}).get("maxSize"),
                            "desired_size": nodegroup.get("scalingConfig", {}).get("desiredSize"),
                            "capacity_type": nodegroup.get("capacityType"),
                        }
                    )

        except Exception:
            logger.exception(f"EKS scan failed | region={region}")
            raise
