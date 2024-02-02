import pytest
from autoscaler import AtlasAutoScaler
from models import AtlasCluster, AtlasProcess, AtlasPerformanceStats


@pytest.mark.parametrize("cluster_size, measurements, result", [
    ('M40',
     {'DISK_PARTITION_IOPS_READ': [
         AtlasPerformanceStats(None, 1253.62),
         AtlasPerformanceStats(None, 1232.57)],
         'DISK_PARTITION_IOPS_WRITE': [
             AtlasPerformanceStats(None, 1.68),
             AtlasPerformanceStats(None,
                                   1.81)]}, 'M50'),
    ('M30',
     {'DISK_PARTITION_IOPS_READ': [
         AtlasPerformanceStats(None, 1500),
         AtlasPerformanceStats(None, 1500)],
         'DISK_PARTITION_IOPS_WRITE': [
             AtlasPerformanceStats(None, 0),
             AtlasPerformanceStats(None,
                                   0)]}, 'M40'),
    ('M30',
     {'DISK_PARTITION_IOPS_READ': [
         AtlasPerformanceStats(None, 0),
         AtlasPerformanceStats(None, 0)],
         'DISK_PARTITION_IOPS_WRITE': [
             AtlasPerformanceStats(None, 1500),
             AtlasPerformanceStats(None,
                                   1500)]}, 'M40'),
    ('M30',
     {'DISK_PARTITION_IOPS_READ': [
         AtlasPerformanceStats(None, 0),
         AtlasPerformanceStats(None, 1500)],
         'DISK_PARTITION_IOPS_WRITE': [
             AtlasPerformanceStats(None, 0),
             AtlasPerformanceStats(None,
                                   0)]}, 'M30'),
    ('M30',
     {'DISK_PARTITION_IOPS_READ': [
         AtlasPerformanceStats(None, 0),
         AtlasPerformanceStats(None, 0)],
         'DISK_PARTITION_IOPS_WRITE': [
             AtlasPerformanceStats(None, 0),
             AtlasPerformanceStats(None,
                                   0)]}, 'M30'),
    ('M40',
     {'DISK_PARTITION_IOPS_READ': [
         AtlasPerformanceStats(None, 0),
         AtlasPerformanceStats(None, 0)],
         'DISK_PARTITION_IOPS_WRITE': [
             AtlasPerformanceStats(None, 0),
             AtlasPerformanceStats(None,
                                   0)]}, 'M30'),
    ('M40',
     {'DISK_PARTITION_IOPS_READ': [
         AtlasPerformanceStats(None, 0),
         AtlasPerformanceStats(None, 0)],
         'DISK_PARTITION_IOPS_WRITE': [
             AtlasPerformanceStats(None, 4000),
             AtlasPerformanceStats(None,
                                   0)]}, 'M40')
])
def test_auto_scaling(cluster_size, measurements, result):
    scaler = AtlasAutoScaler('Dummy', 'Dummy', 'Dummy', 'Dummy')
    scaler.cluster = AtlasCluster('Dummy')
    scaler.cluster.size = cluster_size
    scaler.cluster.processes = [AtlasProcess("url1", 'REPLICA_PRIMARY'), AtlasProcess("url2", 'REPLICA_SECONDARY'),
                                AtlasProcess("url3", 'REPLICA_SECONDARY')]
    for proc in scaler.cluster.processes:
        proc.metrics = measurements
    assert scaler.get_target_size() == result
