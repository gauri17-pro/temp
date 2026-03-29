# AttendTrack 📋

A sleek Flask attendance management system for teachers with PostgreSQL backend.

## Features
- 🔐 Teacher authentication (register / login)
- 🗂 Multiple attendance catalogues per teacher
- 👥 Add / remove students with roll numbers
- ✅ Mark present / absent with toggle UI
- 📅 View & edit attendance by date
- 📊 Attendance percentage reports per student
- 🐳 Docker + PostgreSQL ready

## Quick Start (Docker)

```bash
# 1. Clone and enter the directory
cd attendance-app

# 2. Build and start
docker compose up --build

Note: Execute  dos2unix entrypoint.sh before docker compose up command if running on Windows 

# 3. Open http://localhost:5000
# Demo login: teacher / password123
```

## Local Development (without Docker)

```bash
# 1. Create a virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set environment variables
export DB_HOST=localhost DB_USER=postgres DB_PASSWORD=postgres DB_NAME=attendance_db

# 4. Run
python app.py
```

## Environment Variables

| Variable     | Default           | Description                   |
|--------------|-------------------|-------------------------------|
| DB_USER      | postgres          | PostgreSQL username            |
| DB_PASSWORD  | postgres          | PostgreSQL password            |
| DB_HOST      | db                | PostgreSQL host                |
| DB_PORT      | 5432              | PostgreSQL port                |
| DB_NAME      | attendance_db     | Database name                  |
| SECRET_KEY   | (insecure)        | Flask session secret key       |

## Project Structure

```
attendance-app/
├── app.py                  # Flask app + routes + models
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── entrypoint.sh
├── .env.example
└── templates/
    ├── base.html
    ├── login.html
    ├── register.html
    ├── dashboard.html
    ├── new_catalogue.html
    ├── catalogue.html      # Main attendance view
    └── report.html
```

## Deploying your application on EKS

## Using Cloudshell to install eksctl, helm and kubseal

- kubectl is already present on cloudshell 

- Install eksctl
```
curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin
```

- Install helm
```
curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-4
chmod 700 get_helm.sh
./get_helm.sh
```

- Install kubeseal
```
KUBESEAL_VERSION='0.35.0' 
curl -OL "https://github.com/bitnami-labs/sealed-secrets/releases/download/v${KUBESEAL_VERSION:?}/kubeseal-${KUBESEAL_VERSION:?}-linux-amd64.tar.gz"
tar -xvzf kubeseal-${KUBESEAL_VERSION:?}-linux-amd64.tar.gz kubeseal
sudo install -m 755 kubeseal /usr/local/bin/kubeseal
```

- Launching an EKS cluster
```
eksctl create cluster -f eks-config.yml
```

- Install sealed-secrets controller
```
helm repo add sealed-secrets https://bitnami-labs.github.io/sealed-secrets
helm repo update sealed-secrets
helm install sealed-secrets-controller sealed-secrets/sealed-secrets --namespace kube-system
```

- Install ArgoCD 
```
kubectl create namespace argocd
kubectl apply -n argocd --server-side --force-conflicts -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```

```
kubectl patch svc argocd-server -n argocd -p '{"spec": {"type": "LoadBalancer"}}'
```

```
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d; echo
```

- All the manifests are written inside the k8s-manifests. You can Helmify them.

- We will be implementing HPA (Horizontal Pod Autoscaler) which will need Metrics Server installed.
  Inside the EKS we have Metrics server already running. We just need to make a small correction.
```
  kubectl patch deployment metrics-server -n kube-system \
>   --type='merge' \
>   -p '{
>     "spec": {
>       "template": {
>         "metadata": {
>           "labels": {
>             "k8s-app": "metrics-server"
>           }
>         }
>       }
>     }
>   }'
```

- Create the sealed secrets using command below for pulling the images from private docker registry
```
kubectl create secret docker-registry docker-creds \
  --docker-username=gauris17 \
  --docker-password=YourPassword \
  --namespace attendance-app \
  --dry-run=client -o yaml | \
kubeseal \
  --controller-name sealed-secrets-controller \
  --controller-namespace kube-system \
  --namespace attendance-app \
  -o yaml | tee docker-sealedsecret.yml
```

- Create the DB related secrets 
```
kubectl create secret generic db-secrets \
  --from-literal=DB_USER=postgres --from-literal=DB_PASSWORD=postgres \
  --namespace attendance-app \
  --dry-run=client -o yaml | \
kubeseal \
  --controller-name sealed-secrets-controller \
  --controller-namespace kube-system \
  --namespace attendance-app \
  -o yaml | tee db-sealedsecret.yml
```

## Deploy prometheus and grafana 

```
helm install monitoring prometheus-community/kube-prometheus-stack
```

#### Expose Prometheus service
```
kubectl get svc
kubectl expose svc prometheus-operated --type=LoadBalancer --port=9090 --target-port=9090 --name=prometheus-ext
```

#### Expose Grafana service
```
kubectl expose svc monitoring-grafana --type=LoadBalancer --port=3000 --target-port=3000 --name=grafana-ext
```

#### Fetch the password
```
kubectl get secret
kubectl get secret --namespace default monitoring-grafana -o jsonpath="{.data.admin-password}" | base64 --decode; echo
```

#### Dashboard for Kubernetes monitoring

- 15760
- 1860
