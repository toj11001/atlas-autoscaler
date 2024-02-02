import yaml

# sleep time between control loop iterations in seconds
SLEEP_TIME = 60

# GCP size matrix for region Frankfurt as of 19.02.2021, used to decide when to scale and how to scale
CLUSTER_SIZES = {'M30': {'name': 'M30', 'cpus': 2, 'ram': 7.5, 'max_disk_size': 512, 'DISK_PARTITION_IOPS_READ': 1200,
                     'DISK_PARTITION_IOPS_WRITE': 1200,
                     'DISK_PARTITION_IOPS_TOTAL': 2400, 'next_size': 'M40', 'prev_size': None},
             'M40': {'name': 'M40', 'cpus': 4, 'ram': 15, 'max_disk_size': 1024, 'DISK_PARTITION_IOPS_READ': 2400,
                     'DISK_PARTITION_IOPS_WRITE': 2400,
                     'DISK_PARTITION_IOPS_TOTAL': 4800, 'next_size': 'M50', 'prev_size': 'M30'},
             'M50': {'name': 'M50', 'cpus': 8, 'ram': 30, 'max_disk_size': 4096, 'DISK_PARTITION_IOPS_READ': 4800,
                     'DISK_PARTITION_IOPS_WRITE': 4800,
                     'DISK_PARTITION_IOPS_TOTAL': 9000, 'next_size': 'M60', 'prev_size': 'M40'},
             'M60': {'name': 'M60', 'cpus': 16, 'ram': 60, 'max_disk_size': 4096, 'DISK_PARTITION_IOPS_READ': 9600,
                     'DISK_PARTITION_IOPS_WRITE': 9600,
                     'DISK_PARTITION_IOPS_TOTAL': 19200, 'next_size': 'M80', 'prev_size': 'M50'},
                 'M80': {'name': 'M80', 'cpus': 32, 'ram': 120, 'max_disk_size': 4096, 'DISK_PARTITION_IOPS_READ': 22500,
                     'DISK_PARTITION_IOPS_WRITE': 22500, 'DISK_PARTITION_IOPS_TOTAL': 45000,
                     'next_size': 'M200', 'prev_size': 'M50'},
                 'M200': {'name': 'M200', 'cpus': 64, 'ram': 240, 'max_disk_size': 4096, 'DISK_PARTITION_IOPS_READ': 45000,
                      'DISK_PARTITION_IOPS_WRITE': 45000, 'DISK_PARTITION_IOPS_TOTAL': 90000,
                      'next_size': 'M300', 'prev_size': 'M80'},
                 'M300': {'name': 'M300', 'cpus': 96, 'ram': 360, 'max_disk_size': 4096, 'DISK_PARTITION_IOPS_READ': 60000,
                      'DISK_PARTITION_IOPS_WRITE': 60000, 'DISK_PARTITION_IOPS_TOTAL': 100000,
                      'next_size': None, 'prev_size': 'M200'},
                 }

with open("settings.yaml", 'r') as stream:
    settings = yaml.safe_load(stream)
    PROJECT_ID = settings['target']['project_id']
    CLUSTER_NAME = settings['target']['cluster_name']
    CLUSTER_URL = settings['target']['cluster_url']
    PRIVATE_KEY = settings['api_access'].get('private_key', None)
    PUBLIC_KEY = settings['api_access']['public_key']
