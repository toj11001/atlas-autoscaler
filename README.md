IOPS-based autoscaler for MongoDB Atlas
----
#### Config file
The required settings are read from the *settings.yaml* that should be created with the following content:
```
target:
  project_id: # id of the project that contains the cluster to be managed
  cluster_name: # the name of the cluster to be managed
  cluster_url: # the MongoDB connections string, required only for load generation
api_access:
  public_key: # key_id
  private_key: # secret
```