from datetime import datetime


class AtlasPerformanceStats:
    """
    Represents a single measurement
    """
    def __init__(self, point_in_time, value):
        self.time = point_in_time
        self.value = value

    def __repr__(self):
        return f'({self.time}, {self.value})'


class AtlasProcess:
    """
    Represents a member process of a replica set or a sharded cluster
    """
    def __init__(self, name, url, type_name):
        self.name = name
        self.url = url
        self.disk_monitoring_link = None
        self.role = type_name
        # metrics will contain the time series data, the dictionary key is the name of the metric, the value is
        # an array of AtlasPerformanceStats
        self.metrics = {}
        self.timestamps = None

    @staticmethod
    def build_list(points):
        # ToDo: think about pruning stuff here
        return [AtlasPerformanceStats(t['timestamp'], t['value']) for t in points if t['value'] is not None]

    def parse_metrics(self, raw_metrics):
        for metric in raw_metrics:
            # if metric['name'] in METRICS_TO_PROCESS:
            self.metrics[metric['name']] = self.build_list(metric['dataPoints'])

    def group_metrics_by_timestamp(self):
        # for every timestamp see build a dict of metric:value pairs
        timestamps = {}
        for metric_name, value_list in self.metrics.items():
            for stat in value_list:
                group_time = datetime.strptime(stat.time, "%Y-%m-%dT%H:%M:%SZ").replace(second=0)
                if timestamps.get(group_time, None) is None:
                    timestamps[group_time] = {metric_name: stat.value}
                else:
                    timestamps[group_time][metric_name] = stat.value
        self.timestamps = timestamps


class AtlasCluster:
    """
    Represents an Atlas Cluster
    """
    def __init__(self, cluster_name):
        assert cluster_name
        self.name = cluster_name
        self.region = None
        self.provider = None
        self.processes: [AtlasProcess] = []
        self.state = None
        self.size = None
        self.diskSizeGB = None

    def get_primary_process(self):
        primary = None
        for proc in self.processes:
            if proc.role == 'REPLICA_PRIMARY':
                primary = proc
                break

        return primary

    def build_timestamps_with_metrics(self):
        for proc in self.processes:
            proc.group_metrics_by_timestamp()
            