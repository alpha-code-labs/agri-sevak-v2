# Azure Deployment — Service Inventory

## Azure Cloud Resources (kissan-rg)

| Service | Name | Type | Function |
|---|---|---|---|
| AKS Cluster | `kcc-aks-cluster` | Microsoft.ContainerService/managedClusters | Kubernetes cluster (1 node, Standard_B2ms, 2 vCPU / 8GB RAM). Hosts all application pods. |
| Azure Cache for Redis | `kcc-redis` | Microsoft.Cache/Redis | Basic C0 tier. Session storage, message deduplication (SET NX EX), and agent memory. Endpoint: `kcc-redis.redis.cache.windows.net:6380` (TLS). |
| Azure Container Registry | `kissanacr` | Microsoft.ContainerRegistry/registries | Basic tier. Stores Docker images: `webhook-receiver` and `agent-worker`. |
| Log Analytics Workspace | `workspacekissanrgbe3a` | Microsoft.OperationalInsights/workspaces | Auto-created by AKS for cluster monitoring and diagnostics. |

## AKS Managed Infrastructure (MC_kissan-rg_kcc-aks-cluster_centralindia)

These are auto-managed by AKS — do not modify directly.

| Service | Name | Function |
|---|---|---|
| VM Scale Set | `aks-nodepool1-18110775-vmss` | The actual compute node (Standard_B2ms) running all pods. |
| Load Balancer | `kubernetes` | Standard Load Balancer routing external traffic (port 80/443) to the Nginx Ingress controller inside the cluster. |
| Public IP | `kubernetes-a41940b5cf4c84313b12b03743adfb81` | External IP `20.244.72.1` assigned to the Load Balancer for Nginx Ingress. |
| Public IP | `aa4b9247-3758-4d5d-8d6c-1c86438a96ed` | Outbound IP for cluster egress (pods making external API calls). |
| Virtual Network | `aks-vnet-30629609` | Private network for all cluster nodes and pods. |
| Network Security Group | `aks-agentpool-30629609-nsg` | Firewall rules allowing inbound traffic on ports 80/443 from the Internet. |
| Managed Identity | `kcc-aks-cluster-agentpool` | Identity used by the node to pull images from ACR and manage Azure resources. |

## Kubernetes Resources (namespace: kcc)

### Application Pods

| Deployment | Image | Replicas | Function |
|---|---|---|---|
| `webhook-receiver` | `kissanacr.azurecr.io/webhook-receiver:latest` | 1 | FastAPI app. Receives WhatsApp webhooks from Meta, verifies HMAC, deduplicates via Redis, routes messages to Kafka topics. Exposed at `http://20.244.72.1/webhook`. |
| `text-worker` | `kissanacr.azurecr.io/agent-worker:latest` | 1 | Kafka consumer for `farmer-messages-text` topic. Runs the LangGraph agent with 5 tools (crop detector, RAG retriever, safety checker, weather fetcher, image analyzer). Loads MuRIL crop classifier + sentence-transformer on startup. Sends WhatsApp responses via Graph API. |

### Infrastructure Pods

| Deployment | Image | Function |
|---|---|---|
| `redpanda` | `redpandadata/redpanda:v24.1.1` | Kafka-compatible message broker. 3 topics: `farmer-messages-text` (6 partitions), `farmer-messages-image` (3 partitions), `farmer-messages-voice` (3 partitions). Replaces Azure Event Hubs to save cost. |
| `ingress-nginx-controller` | `registry.k8s.io/ingress-nginx/controller:v1.14.3` | Nginx reverse proxy. Routes external HTTP traffic to the webhook-receiver service. Rate limiting, proxy timeouts. |
| `keda-operator` | `ghcr.io/kedacore/keda:2.19.0` | Kubernetes Event-Driven Autoscaler. Watches Kafka consumer lag and scales worker pods automatically (not yet configured with ScaledObjects). |
| `keda-admission-webhooks` | `ghcr.io/kedacore/keda-admission-webhooks:2.19.0` | Validates KEDA custom resources (ScaledObjects, TriggerAuthentications). |
| `keda-operator-metrics-apiserver` | `ghcr.io/kedacore/keda-metrics-apiserver:2.19.0` | Exposes Kafka lag metrics to the Kubernetes HPA controller for autoscaling decisions. |

### Configuration

| Resource | Type | Function |
|---|---|---|
| `kcc-config` | ConfigMap | Non-sensitive configuration: Kafka bootstrap servers, Redis URL, Pinecone index name, Gemini model names, agent timeout, similarity threshold, log level. |
| `kcc-secrets` | Secret | Sensitive credentials: Gemini API keys, Pinecone API key, WhatsApp access token, WhatsApp verify token, WhatsApp app secret, phone number ID, Azure Blob connection string. |

### Networking

| Resource | Type | Function |
|---|---|---|
| `kcc-ingress` | Ingress | Routes `/webhook` and `/health` to the webhook-receiver service via Nginx. External IP: `20.244.72.1`. |
| `webhook-receiver` | ClusterIP Service | Internal service exposing webhook-receiver pods on port 80 (target 8080). |
| `redpanda` | ClusterIP Service | Internal service exposing Redpanda on port 9092. Accessed by workers at `redpanda.kcc.svc.cluster.local:9092`. |

## External Services (not on Azure)

| Service | Function |
|---|---|
| Pinecone (free tier) | Vector database. Stores 4,742 RAG embeddings for crop advisory responses. Queried by the RAG retriever tool. |
| Google Gemini API | LLM for the LangGraph agent (gemini-2.0-flash), safety auditing, image analysis, and crop detection fallback. |
| Meta WhatsApp Business API | Sends/receives WhatsApp messages. Webhook URL to be configured: `https://<domain>/webhook`. |
| OpenWeatherMap API | 7-day weather forecast for Haryana districts. Used by the weather fetcher tool. |

## Monthly Cost Breakdown

| Resource | Estimated Cost (INR) |
|---|---|
| AKS VM (Standard_B2ms) | ~₹2,500 |
| Standard Load Balancer | ~₹1,500 |
| Redis Basic C0 | ~₹1,350 |
| OS Disk (128GB managed) | ~₹700 |
| ACR Basic | ~₹420 |
| Public IP (Standard) | ~₹300 |
| **Total** | **~₹6,770/month** |
