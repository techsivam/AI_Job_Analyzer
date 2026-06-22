## Dockerfile

You can **copy and paste it directly** into a file named `Dockerfile`.

```dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN pip install --no-cache-dir -e .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]

```

## Kubernetes Deployment File

You can **copy and paste it directly** into a file named `k8s-deployment.yaml`.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: streamlit-app
  labels:
    app: streamlit
spec:
  replicas: 1
  selector:
    matchLabels:
      app: streamlit
  template:
    metadata:
      labels:
        app: streamlit
    spec:
      containers:
        - name: streamlit-container
          image: streamlit-app:latest
          imagePullPolicy: IfNotPresent
          ports:
            - containerPort: 8501
            
---
apiVersion: v1
kind: Service
metadata:
  name: streamlit-service
spec:
  type: LoadBalancer
  selector:
    app: streamlit
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8501

```
## FileBeat Deployment File

You can **copy and paste it directly** into a file named `filebeat.yaml`.

```yaml
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: filebeat-config
  namespace: logging
  labels:
    k8s-app: filebeat
data:
  filebeat.yml: |-
    filebeat.inputs:
    - type: container
      paths:
        - /var/log/containers/*.log
      processors:
        - add_kubernetes_metadata:
            host: ${NODE_NAME}
            matchers:
            - logs_path:
                logs_path: "/var/log/containers/"
    processors:
      - add_cloud_metadata:
      - add_host_metadata:
    output.logstash:
      hosts: ["logstash.logging.svc.cluster.local:5044"]

---
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: filebeat
  namespace: logging
  labels:
    k8s-app: filebeat
spec:
  selector:
    matchLabels:
      k8s-app: filebeat
  template:
    metadata:
      labels:
        k8s-app: filebeat
    spec:
      serviceAccountName: filebeat
      terminationGracePeriodSeconds: 30
      hostNetwork: true
      dnsPolicy: ClusterFirstWithHostNet
      containers:
      - name: filebeat
        image: docker.elastic.co/beats/filebeat:7.17.28
        args: [
          "-c", "/etc/filebeat.yml",
          "-e",
        ]
        env:
        - name: NODE_NAME
          valueFrom:
            fieldRef:
              fieldPath: spec.nodeName
        securityContext:
          runAsUser: 0
        resources:
          limits:
            memory: 200Mi
          requests:
            cpu: 100m
            memory: 100Mi
        volumeMounts:
        - name: config
          mountPath: /etc/filebeat.yml
          readOnly: true
          subPath: filebeat.yml
        - name: data
          mountPath: /usr/share/filebeat/data
        - name: varlibdockercontainers
          mountPath: /var/lib/docker/containers
          readOnly: true
        - name: varlog
          mountPath: /var/log
          readOnly: true
      volumes:
      - name: config
        configMap:
          defaultMode: 0640
          name: filebeat-config
      - name: varlibdockercontainers
        hostPath:
          path: /var/lib/docker/containers
      - name: varlog
        hostPath:
          path: /var/log
     
      - name: data
        hostPath:
          
          path: /var/lib/filebeat-data
          type: DirectoryOrCreate
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: filebeat
subjects:
- kind: ServiceAccount
  name: filebeat
  namespace: logging
roleRef:
  kind: ClusterRole
  name: filebeat
  apiGroup: rbac.authorization.k8s.io
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: filebeat
  namespace: logging
subjects:
  - kind: ServiceAccount
    name: filebeat
    namespace: logging
roleRef:
  kind: Role
  name: filebeat
  apiGroup: rbac.authorization.k8s.io
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: filebeat-kubeadm-config
  namespace: logging
subjects:
  - kind: ServiceAccount
    name: filebeat
    namespace: logging
roleRef:
  kind: Role
  name: filebeat-kubeadm-config
  apiGroup: rbac.authorization.k8s.io
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: filebeat
  labels:
    k8s-app: filebeat
rules:
- apiGroups: [""] 
  resources:
  - namespaces
  - pods
  - nodes
  verbs:
  - get
  - watch
  - list
- apiGroups: ["apps"]
  resources:
    - replicasets
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: filebeat
  namespace: logging
  labels:
    k8s-app: filebeat
rules:
  - apiGroups:
      - coordination.k8s.io
    resources:
      - leases
    verbs: ["get", "create", "update"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: filebeat-kubeadm-config
  namespace: logging
  labels:
    k8s-app: filebeat
rules:
  - apiGroups: [""]
    resources:
      - configmaps
    resourceNames:
      - kubeadm-config
    verbs: ["get"]
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: filebeat
  namespace: logging
  labels:
    k8s-app: filebeat
---
```

## LogStash Deployment File

You can **copy and paste it directly** into a file named `logstash.yaml`.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: logstash-config
  namespace: logging
data:
  logstash.conf: |
    input {
      beats {
        port => 5044
      }
    }

    filter {
      
    }

    output {
      elasticsearch {
        hosts => ["http://elasticsearch.logging.svc.cluster.local:9200"]
        index => "filebeat-%{+YYYY.MM.dd}"
      }
    }
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: logstash
  namespace: logging
spec:
  replicas: 1
  selector:
    matchLabels:
      app: logstash
  template:
    metadata:
      labels:
        app: logstash
    spec:
      containers:
      - name: logstash
        image: docker.elastic.co/logstash/logstash:7.17.0
        ports:
        - containerPort: 5044
        - containerPort: 9600
        volumeMounts:
        - name: config-volume
          mountPath: /usr/share/logstash/pipeline/logstash.conf
          subPath: logstash.conf
      volumes:
      - name: config-volume
        configMap:
          name: logstash-config
          items:
          - key: logstash.conf
            path: logstash.conf
---
apiVersion: v1
kind: Service
metadata:
  name: logstash
  namespace: logging
spec:
  selector:
    app: logstash
  ports:
    - protocol: TCP
      port: 5044
      targetPort: 5044

```

## ElasticSearch Deployment File

You can **copy and paste it directly** into a file named `elasticsearch.yaml`.

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: elasticsearch-pvc
  namespace: logging
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 2Gi
  storageClassName: standard
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: elasticsearch
  namespace: logging
spec:
  replicas: 1
  selector:
    matchLabels:
      app: elasticsearch
  template:
    metadata:
      labels:
        app: elasticsearch
    spec:
      containers:
        - name: elasticsearch
          image: docker.elastic.co/elasticsearch/elasticsearch:8.11.1
          env:
            - name: discovery.type
              value: single-node
            - name: ES_JAVA_OPTS
              value: "-Xms512m -Xmx512m"
            - name: xpack.security.enabled
              value: "false"
          ports:
            - containerPort: 9200
          resources:
            limits:
              memory: "2Gi"
              cpu: "1"
            requests:
              memory: "1Gi"
              cpu: "500m"
          volumeMounts:
            - mountPath: /usr/share/elasticsearch/data
              name: elasticsearch-storage
      volumes:
        - name: elasticsearch-storage
          persistentVolumeClaim:
            claimName: elasticsearch-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: elasticsearch
  namespace: logging
spec:
  selector:
    app: elasticsearch
  ports:
    - protocol: TCP
      port: 9200
      targetPort: 9200
      
```

## Kibana Deployment File

You can **copy and paste it directly** into a file named `kibana.yaml`.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kibana
  namespace: logging
spec:
  replicas: 1
  selector:
    matchLabels:
      app: kibana
  template:
    metadata:
      labels:
        app: kibana
    spec:
      containers:
        - name: kibana
          image: docker.elastic.co/kibana/kibana:7.17.0
          env:
            - name: ELASTICSEARCH_HOSTS
              value: http://elasticsearch:9200
          ports:
            - containerPort: 5601
---
apiVersion: v1
kind: Service
metadata:
  name: kibana
  namespace: logging
spec:
  type: NodePort
  selector:
    app: kibana
  ports:
    - port: 5601
      nodePort: 30601
```

## GCP Cloud Setup

---

### 1. Create a VM Instance on Google Cloud

1. Go to **Compute Engine → VM Instances**
2. Click **Create Instance**

**Basic Configuration**

* **Name:** `Whatever you want to name`
* **Machine Type:**

  * Series: **E2**
  * Preset: **Standard**
  * Memory: **16 GB RAM**
* **Boot Disk:**

  * Size: **150 GB**
  * Image: **Ubuntu 24.04 LTS**
* **Networking:**

  * Enable **HTTP** and **HTTPS** traffic and **Port Forwarding** turned on

Click **Create** to launch the instance.

---

### 2. Connect to the VM

* Use the **SSH** button in the Google Cloud Console to connect to the VM directly from the browser.

---

### 3. Configure the VM Instance

#### Clone the GitHub Repository

```bash
git clone https://github.com/data-guru0/TESTING-9.git ( Whatver your Github repo link )
ls
cd TESTING-9
ls
```

You should now see the project files inside the VM.

---

### 4. Install Docker

1. Open a browser and search for **“Install Docker on Ubuntu”**
2. Open the **official Docker documentation** (`docs.docker.com`)
3. Copy and paste the **first command block** into the VM terminal
4. Copy and paste the **second command block**
5. Test the Docker installation:

```bash
docker run hello-world
```

---

### 5. Run Docker Without `sudo`

From the same Docker documentation page, scroll to **Post-installation steps for Linux** and run **all four commands** one by one.

The last command is used to verify Docker works without `sudo`.

---

### 6. Enable Docker to Start on Boot

From the section **Configure Docker to start on boot**, run:

```bash
sudo systemctl enable docker.service
sudo systemctl enable containerd.service
```

---

### 7. Verify Docker Setup

```bash
systemctl status docker
docker ps
docker ps -a
```

Expected results:

* Docker service shows **active (running)**
* No running containers
* `hello-world` container appears in exited state

---

### 8. Configure Minikube Inside the VM

#### Install Minikube

1. Search for **Install Minikube**
2. Open the official website: `minikube.sigs.k8s.io`
3. Select:

   * **OS:** Linux
   * **Architecture:** x86
   * **Installation Type:** Binary

Copy and run the installation commands provided on the website.

---

#### Start the Minikube Cluster

```bash
minikube start
```

Minikube uses **Docker internally**, which is why Docker was installed first.

---


---

### 9. Verify Kubernetes & Minikube Setup

```bash
minikube status
minikubr kubectl get nodes
minikube kubectl cluster-info
docker ps
```

Expected results:

* All Minikube components are running
* A single `minikube` node is visible
* Kubernetes cluster information is accessible
* Minikube container is running in Docker

---

### 10. Install kubectl

 - Search: `Install kubectl`
  - Instead of installing manually, go to the **Snap section** (below on the same page)

  ```bash
  sudo snap install kubectl --classic
  ```

  - Verify installation:

    ```bash
    kubectl version --client
    ```

### 11. Configure GCP Firewall (If Needed)

If Jenkins does not load, create a firewall rule:

* **Name:** `allow-apps`
* **Description:** Allow all traffic (for Jenkins demo)
* **Logs:** Off
* **Network:** default
* **Direction:** Ingress
* **Action:** Allow
* **Targets:** All instances
* **Source IP ranges:** `0.0.0.0/0`
* **Allowed protocols and ports:** All

---


## 🔗 Interlink GitHub with Local Machine and VM Instance

### 🛠️ Configure Git (One-time setup)
```bash
git config --global user.email "gyrogodnon@gmail.com"
git config --global user.name "data-guru0"
````

- Use your own email and username

```bash
git add .
git commit -m "commit"
git push origin main
```

### 🔐 When Prompted

```text
Username: data-guru0
Password: GitHub token (paste it — it will be invisible)
```

> ⚠️ GitHub does not accept account passwords.
> Use a **Personal Access Token (PAT)** as the password.

✅ VS Code and VM are now successfully linked with GitHub

---


##  Build and Deploy Your App on VM

### Point Docker to Minikube
```bash
eval $(minikube docker-env)
````


### Build Docker Image

```bash
docker build -t streamlit-app:latest .
```


### Deploy Application to Kubernetes

```bash
kubectl apply -f k8s-deployment.yaml
```


### Check Pod Status

```bash
kubectl get pods
```

> You will see the pods running.


### Expose the App (Port Forwarding)

```bash
kubectl port-forward svc/streamlit-service 8501:80 --address 0.0.0.0
```

- Make sure to give correct service name.


### ✅ Access the Application

* Copy the **External IP**
* Open browser and visit:
- http://EXTERNAL-IP:8501

🎉 Your application is now live..
---

# ✅ ELK Stack Setup on Kubernetes with Filebeat - Step-by-Step Guide

- Make sure in VM you are inside your Github repo that you cloned and interconnected.
- If you are in root directory of VM you will get error..
---

##  Step 1: Create a Namespace for Logging

```bash
kubectl create namespace logging
```
➡️ *This creates an isolated Kubernetes namespace called `logging` to keep all ELK components organized.*

---
##  Step 2: Deploy Filebeat

```bash
kubectl apply -f filebeat.yaml
```
➡️ *Deploys Filebeat to collect logs from all pods/nodes and send to Logstash.*

```bash
kubectl get all -n logging
```
➡️ *Checks all resources (pods, services, etc.) to confirm everything is running.*

✅ **Filebeat setup done...**

---

##  Step 3: Deploy Logstash

```bash
kubectl apply -f logstash.yaml
```
➡️ *Deploys Logstash to process and forward logs.*

```bash
kubectl get pods -n logging
```
➡️ *Ensure Logstash is running.*

✅ **Logstash setup done...**

---

##  Step 4: Deploy Elasticsearch

```bash
kubectl apply -f elasticsearch.yaml
```
➡️ *Applies your Elasticsearch deployment configuration.*

```bash
kubectl get pods -n logging
```
➡️ *Checks if Elasticsearch pods are up and running.*

```bash
kubectl get pvc -n logging
```
➡️ *Checks PersistentVolumeClaims — these should be in `Bound` state (storage is allocated).*


✅ **Elasticsearch setup done...**

---

##  Step 5: Deploy Kibana

```bash
kubectl apply -f kibana.yaml
```
➡️ *Deploys Kibana, the frontend for Elasticsearch.*

```bash
kubectl get pods -n logging
```
➡️ *Wait until the Kibana pod is in `Running` state (might take a few minutes).*

```bash
kubectl port-forward -n logging svc/kibana 5601:5601 --address 0.0.0.0
```
➡️ *This makes Kibana accessible at `http://<your-ip>:5601`.*

✅ **Kibana setup done...**

---
---

##  Step 6: Setup Index Patterns in Kibana

1. Open Kibana in browser → `http://<your-ip>:5601`
2. Click **"Explore on my own"**
3. Go to **Stack Management** from the left panel
4. Click **Index Patterns**
5. Create new index pattern:
   - Pattern name: `filebeat-*`
   - Timestamp field: `@timestamp`
6. Click **Create Index Pattern**

➡️ *This tells Kibana how to search and filter logs coming from Filebeat.*

---

##  Step 7: Explore Logs

1. In the left panel, click **"Analytics → Discover"**
2. You will see logs collected from Kubernetes cluster!
3. Use filters like:
   - `kubernetes.container.name` to filter logs from specific pods like Filebeat, Kibana, Logstash, etc.

✅ **Done! Now you can monitor and analyze your K8s logs using ELK + Filebeat. 🎉**