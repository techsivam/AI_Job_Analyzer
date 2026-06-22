# JobAnalyzer - Local Kubernetes Deployment Guide

This guide provides step-by-step instructions to deploy the JobAnalyzer Streamlit application in a local Kubernetes environment using Docker Desktop.

## Prerequisites

Ensure you have the following installed:
- **Docker Desktop** (with Kubernetes enabled) - [Download](https://www.docker.com/products/docker-desktop)
- **kubectl** (usually comes with Docker Desktop)
- **Python 3.8+** (for local development/testing)
- **OpenAI API Key** - [Get from OpenAI](https://platform.openai.com/api-keys)

### Verify Installation

```bash
docker --version
kubectl version --client
```

## Step 1: Enable Kubernetes in Docker Desktop

1. Open **Docker Desktop**
2. Go to **Settings** → **Kubernetes**
3. Check **Enable Kubernetes**
4. Click **Apply & Restart**
5. Wait for Kubernetes to start (check the status icon in the bottom-left)

Verify Kubernetes is running:
```bash
kubectl cluster-info
kubectl get nodes
```

## Step 2: Build the Docker Image

Navigate to the project root directory and build the image:

```bash
docker build -t streamlit-app:latest .
```

**Note**: Ensure you have a Dockerfile in the root directory. If not, create one:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose Streamlit port
EXPOSE 8501

# Set Streamlit configuration
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_LOGGER_LEVEL=info

# Run the application
CMD ["streamlit", "run", "app.py", "--server.runOnSave=true"]
```

Verify the image was built:
```bash
docker images | grep streamlit-app
```

## Step 3: Load Image into Kubernetes (Docker Desktop)

Since you're using Docker Desktop's built-in Kubernetes, the image is automatically available. However, ensure the image pull policy is set correctly.

## Step 4: Deploy to Kubernetes

Apply the Kubernetes deployment configuration:

```bash
kubectl apply -f k8s-deployment.yaml
```

Verify the deployment:
```bash
kubectl get deployments
kubectl get pods
kubectl get services
```

Expected output:
```
NAME             READY   STATUS    RESTARTS   AGE
streamlit-app    1/1     Running   0          10s

NAME                    TYPE           CLUSTER-IP     EXTERNAL-IP   PORT(S)        AGE
streamlit-service       LoadBalancer   10.96.x.x      localhost     80:xxxxx/TCP   10s
```

## Step 5: Access the Application

### Option A: Using LoadBalancer Service (Recommended)

The service is configured as `LoadBalancer`, so access it via:
```
http://localhost
```

Or check the service port:
```bash
kubectl get service streamlit-service
```

### Option B: Port Forwarding (Alternative)

```bash
kubectl port-forward svc/streamlit-service 8501:8501
```

Then access:
```
http://localhost:8501
```

### Option C: Access Pod Directly

```bash
kubectl port-forward pod/<pod-name> 8501:8501
```

Get pod name:
```bash
kubectl get pods
```

## Step 6: Provide OpenAI API Key

When you open the application in your browser:

1. Navigate to the **Sidebar** (left side)
2. Enter your **OpenAI API Key** in the text field
3. Upload a **Resume** (PDF)
4. Upload a **Job Description** (PDF)
5. Click **Analyze** button

## Troubleshooting

### Check Logs
```bash
# View pod logs
kubectl logs <pod-name>

# Real-time logs
kubectl logs -f <pod-name>
```

### Check Pod Status
```bash
kubectl describe pod <pod-name>
```

### Restart Deployment
```bash
kubectl rollout restart deployment/streamlit-app
```

### Delete and Redeploy
```bash
kubectl delete -f k8s-deployment.yaml
docker build -t streamlit-app:latest .
kubectl apply -f k8s-deployment.yaml
```

### Common Issues

**Issue**: Pod stuck in `ImagePullBackOff`
- **Solution**: Ensure image is built and available: `docker images | grep streamlit-app`
- **Solution**: Check image pull policy in YAML: `imagePullPolicy: IfNotPresent`

**Issue**: Cannot connect to service
- **Solution**: Verify service is running: `kubectl get services`
- **Solution**: Check pod logs: `kubectl logs <pod-name>`
- **Solution**: Try port-forward: `kubectl port-forward svc/streamlit-service 8501:8501`

**Issue**: Port 80 already in use
- **Solution**: Modify k8s-deployment.yaml and change the service port to a different port (e.g., 8080)

**Issue**: OpenAI API errors
- **Solution**: Verify API key is correct
- **Solution**: Check logs for API errors: `kubectl logs <pod-name>`
- **Solution**: Ensure API key has sufficient credits

## Environment Variables

To set environment variables in the pod, modify k8s-deployment.yaml:

```yaml
containers:
  - name: streamlit-container
    image: streamlit-app:latest
    env:
      - name: OPENAI_API_KEY
        valueFrom:
          secretKeyRef:
            name: openai-secret
            key: api-key
```

Create a Kubernetes secret:
```bash
kubectl create secret generic openai-secret --from-literal=api-key=<your-api-key>
```

## Scaling the Application

To scale the deployment:
```bash
kubectl scale deployment streamlit-app --replicas=3
```

## Cleanup

To remove the deployment and service:
```bash
kubectl delete -f k8s-deployment.yaml
```

## Additional Resources

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [Docker Desktop Kubernetes](https://docs.docker.com/desktop/kubernetes/)
- [kubectl Cheat Sheet](https://kubernetes.io/docs/reference/kubectl/cheatsheet/)

---

**Note**: For production deployments, consider:
- Using private container registries
- Implementing resource limits and requests
- Setting up health checks (liveness/readiness probes)
- Configuring ConfigMaps for configuration management
- Using Secrets for sensitive data
```
