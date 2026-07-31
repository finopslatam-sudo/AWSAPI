import logging

from src.aws.scanners.shared import BaseScanner


logger = logging.getLogger(__name__)


class MessagingScanner(BaseScanner):
    """Handles SNS topics and SQS queues."""

    # ------------------------------------------------------------------
    # SNS
    # ------------------------------------------------------------------
    def scan_sns(self, region):
        try:
            sns = self.aws_session.client("sns", region_name=region)
            paginator = sns.get_paginator("list_topics")

            for page in paginator.paginate():
                for topic in page.get("Topics", []):
                    topic_arn = topic["TopicArn"]

                    subscriptions = sns.list_subscriptions_by_topic(
                        TopicArn=topic_arn
                    ).get("Subscriptions", [])

                    self.upsert_resource(
                        service_name="SNS",
                        resource_type="Topic",
                        resource_id=topic_arn,
                        region=region,
                        state="active",
                        tags={},
                        resource_metadata={
                            "subscription_count": len(subscriptions),
                        }
                    )

        except Exception:
            logger.exception(f"SNS scan failed | region={region}")
            raise

    # ------------------------------------------------------------------
    # SQS
    # ------------------------------------------------------------------
    def scan_sqs(self, region):
        try:
            sqs = self.aws_session.client("sqs", region_name=region)
            paginator = sqs.get_paginator("list_queues")

            for page in paginator.paginate():
                for queue_url in page.get("QueueUrls", []):
                    attributes = sqs.get_queue_attributes(
                        QueueUrl=queue_url,
                        AttributeNames=["MessageRetentionPeriod", "ApproximateNumberOfMessages"]
                    ).get("Attributes", {})

                    self.upsert_resource(
                        service_name="SQS",
                        resource_type="Queue",
                        resource_id=queue_url,
                        region=region,
                        state="active",
                        tags={},
                        resource_metadata={
                            "message_retention_period": attributes.get("MessageRetentionPeriod"),
                            "approximate_messages": attributes.get("ApproximateNumberOfMessages"),
                        }
                    )

        except Exception:
            logger.exception(f"SQS scan failed | region={region}")
            raise
