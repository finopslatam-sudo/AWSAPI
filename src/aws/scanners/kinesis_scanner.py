import logging

from src.aws.scanners.shared import BaseScanner


logger = logging.getLogger(__name__)


class KinesisScanner(BaseScanner):
    """Handles Kinesis Data Streams."""

    def scan_kinesis(self, region):
        try:
            kinesis = self.aws_session.client("kinesis", region_name=region)
            paginator = kinesis.get_paginator("list_streams")

            for page in paginator.paginate():
                for stream_name in page.get("StreamNames", []):
                    summary = kinesis.describe_stream_summary(
                        StreamName=stream_name
                    )["StreamDescriptionSummary"]

                    self.upsert_resource(
                        service_name="Kinesis",
                        resource_type="Stream",
                        resource_id=summary["StreamARN"],
                        region=region,
                        state=summary.get("StreamStatus"),
                        tags={},
                        resource_metadata={
                            "name": stream_name,
                            "shard_count": summary.get("OpenShardCount"),
                            "retention_period_hours": summary.get("RetentionPeriodHours"),
                            "stream_mode": summary.get("StreamModeDetails", {}).get("StreamMode"),
                        }
                    )

        except Exception:
            logger.exception(f"Kinesis scan failed | region={region}")
            raise
