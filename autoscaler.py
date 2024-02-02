from datetime import datetime
import time
import pymongo

import requests
from requests.auth import HTTPDigestAuth

from models import AtlasCluster, AtlasProcess
from settings import CLUSTER_SIZES, SLEEP_TIME, CLUSTER_URL

CLIENT = pymongo.MongoClient(CLUSTER_URL)
COLLECTION = CLIENT['scaler']['logs']


class AtlasAutoScaler:

    @staticmethod
    def _parse_members_from_url(uri):
        """
        Parse the mongoURI to extract the RS members
        :param uri: mongodb://cluster0-shard-00-00.kt1ic.mongodb.net:27017,cluster0-shard-00-01.kt1ic.mongodb.net:27017,cluster0-shard-00-02.kt1ic.mongodb.net:27017
        :return: dictionary with all members
        """
        return {member: 1 for member in uri[10:].split(',')}

    @staticmethod
    def _find_link(links, link_name):
        """
        Find the right link within the list of links
        :param links: the links
        :param link_name: the name of the link to find
        :return: the href of the foudn link or None
        """
        for link in links:
            if link['rel'] == link_name:
                return link['href']
        return None

    def __init__(self, project_id, cluster_name, public_key, private_key):
        assert project_id
        assert cluster_name
        assert public_key
        assert private_key

        self.project_id = project_id

        # cluster will contain the last known state
        self.cluster = AtlasCluster(cluster_name)

        # REST API stuff
        self._session = requests.Session()
        self._session.auth = HTTPDigestAuth(public_key, private_key)
        self._base_url = f'https://cloud.mongodb.com/api/atlas/v1.0/groups/{project_id}'
        self._cluster_url = f'{self._base_url}/clusters/{self.cluster.name}'

        self.sensors = None
        self.response_times = [None] * 10

    def get_cluster_state(self):
        """
        This procedure extracts the cluster state and the stats for the last hour with 1 minute granularity
        """
        response = self._session.get(self._cluster_url)
        response.raise_for_status()
        response_parsed = response.json()

        # fill the model with details
        self.cluster.state = response_parsed['stateName']
        self.cluster.size = response_parsed['providerSettings']['instanceSizeName']
        self.cluster.region = response_parsed['providerSettings']['regionName']
        self.cluster.provider = response_parsed['providerSettings']['providerName']
        self.cluster.diskSizeGB = response_parsed['diskSizeGB']

        # the existing APIs do not allow us to easily get all monitoring endpoints for a given cluster
        # this is why the following code parses the uri and extract the members and then gets all the
        # processes in the project and filters out the ones that we do not care about
        rs_members = self._parse_members_from_url(response_parsed['mongoURI'])
        # print(rs_members)

        # get all the processes within the projects
        # ToDo: Handle pagination, since by default only first 100 processes will be returned
        response = self._session.get(f'{self._base_url}/processes')
        response.raise_for_status()

        # filter out and leave only the ones that belong to this cluster
        processes = [proc for proc in response.json()['results'] if f'{proc["userAlias"]}:{proc["port"]}' in rs_members]

        # links list's element with ref "self" will contain the URL for the host monitoring endpoint
        self.cluster.processes = [AtlasProcess(proc['id'], self._find_link(proc['links'], 'self'), proc['typeName']) for
                                  proc in
                                  processes]

        # get the process measurements
        for proc in self.cluster.processes:
            # Get stats for last hour with 1 minute granularity
            response = self._session.get(f'{proc.url}/measurements?granularity=PT1M&period=PT1H')
            response.raise_for_status()
            # extract the metrics
            proc.parse_metrics(response.json()['measurements'])
            # print(proc.metrics)

        # get the disk measurements
        for proc in self.cluster.processes:
            # Get stats for last hour with 1 minute granularity
            response = self._session.get(f'{proc.url}/disks/data/measurements?granularity=PT1M&period=PT1H')
            response.raise_for_status()
            # extract the metrics
            COLLECTION.insert_one(
                {'eventTime': datetime.now(), 'measurements': response.json()['measurements'],
                 'processAndPort': proc.name, 'projectID': '5ff2d0502b9e3507c9c9db82',
                 'diskSizeGB': 40.0, 'state': 'IDLE', 'clusterName': 'db2'})
            proc.parse_metrics(response.json()['measurements'])
            # print(proc.metrics)

    def cluster_is_stable(self):
        """
        Checks if the cluster is in a steady state (no changes are being done)
        :return:
        """
        return self.cluster.state is not None and self.cluster.state == 'IDLE'

    def scale_cluster(self, target_size):
        """
        Scales the cluster to a given size (up or down)
        :param target_size: the target size name
        """

        # the PATCH does not accept just the instanceSizeName, so need to provide a bit more details
        changes = {'providerSettings': {
            'providerName': self.cluster.provider,
            'instanceSizeName': target_size,
            'regionName': self.cluster.region
        }}

        response = self._session.patch(self._cluster_url,
                                       json=changes,
                                       headers={'Content-Type': 'application/json'})
        response.raise_for_status()
        print(f'Scaled the cluster to size: {target_size}')

    def print_cluster_state(self):
        """
        Print cluster state for debugging
        """
        assert self.cluster
        print(f'\nIteration timestamp: {datetime.now()}')
        print(f'Cluster: {self.cluster.name}, state: {self.cluster.state}')
        print(f'Provider: {self.cluster.provider}, instance size: {self.cluster.size}')
        for proc in self.cluster.processes:
            print(f'Role: {proc.role}, id: {proc.url}')
            for metric_name, metric_values in proc.metrics.items():
                print(f'   {metric_name}: {metric_values[-3:]}')

    def get_target_size(self):
        """
        This method decides should the cluster be scaled up or down and returns the target size.

        The scale UP decision is based on any of the Read or Write IOPs being above 50% of the
        defined maximum value for the current size on the primary member of the replica set for 2 minutes.

        The scale DOWN decision is based on both of the Read and Write IOPs being below 10% of the
        defined maximum value for the current size on the primary member of the replica set for 2 minutes.

        :return: the name of the target cluster size, i.e. M50
        """
        assert self.cluster.processes
        assert self.cluster.size
        # the number of minutes to check for scale up and down events
        SCALE_UP_MIN_COUNT, SCALE_DOWN_MIN_COUNT = 2, 2
        # the IO percentages for every metrics
        SCALE_DOWN_PERCENT, SCALE_UP_PERCENT = 0.1, 0.5

        # by default return the current size (no action will be taken)
        result = self.cluster.size

        primary = self.cluster.get_primary_process()
        if primary is None:
            # if there is no primary then nothing should happen
            return result

        # make sure the required metrics are there
        metrics = ['DISK_PARTITION_IOPS_READ', 'DISK_PARTITION_IOPS_WRITE']
        assert all(primary.metrics.get(m, None) for m in metrics)

        # ToDo: add data validation (min required data present, types, etc)

        # scale the cluster one size up if any parameter in metrics oversteps the specified percentage
        # for the last SCALE_UP_MIN_COUNT minutes
        scale_up = any(all(stat.value > SCALE_UP_PERCENT * CLUSTER_SIZES[self.cluster.size][metric] for stat in
                           primary.metrics[metric][-SCALE_UP_MIN_COUNT:]) for metric in metrics)

        if scale_up:
            if CLUSTER_SIZES[self.cluster.size]['next_size'] is not None:
                result = CLUSTER_SIZES[self.cluster.size]['next_size']
            return result

        # scale the cluster one size down if all parameters in metrics were under the specified percentage
        # for the last SCALE_DOWN_MIN_COUNT minutes
        scale_down = not any(any(stat.value > SCALE_DOWN_PERCENT * CLUSTER_SIZES[self.cluster.size][metric] for stat in
                                 primary.metrics[metric][-SCALE_DOWN_MIN_COUNT:]) for metric in metrics)

        if scale_down and CLUSTER_SIZES[self.cluster.size]['prev_size'] is not None:
            result = CLUSTER_SIZES[self.cluster.size]['prev_size']

        return result

    def run_control_loop(self):
        """
        The main control loop that check the load periodically and triggers the scaling
        """

        while True:

            # get the state of the world
            self.get_cluster_state()

            # display it
            self.print_cluster_state()

            # check if we should any actions (if the cluster is in a steady state)
            if self.cluster_is_stable():
                # figure out what needs to be done and do it
                if CLUSTER_SIZES.get(self.cluster.size, None) is None:
                    print('Unknown cluster size')
                else:
                    # calculate what the cluster size should be
                    target_size = self.get_target_size()
                    if target_size != self.cluster.size:
                        # scale up or down
                        self.scale_cluster(target_size)

            # wait for the next control loop iteration
            time.sleep(SLEEP_TIME)
