class AWSServiceDiscovery:
    def __init__(self):
        pass

    def get_filtered_service_statistics(self):
        return {
            "services_in_use": {
                "total_services": 1,
                "total_resources": 1,
                "breakdown": {
                    "dummy-service": 1
                }
            },
            "discovery_metadata": {
                "timestamp": "dummy"
            }
        }
