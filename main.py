from settings import PROJECT_ID, CLUSTER_NAME, PUBLIC_KEY, PRIVATE_KEY
from autoscaler import AtlasAutoScaler

if __name__ == '__main__':
    scaler = AtlasAutoScaler(PROJECT_ID, CLUSTER_NAME, PUBLIC_KEY, PRIVATE_KEY)
    try:
        scaler.run_control_loop()
    except KeyboardInterrupt:
        print('Closing the control loop')
