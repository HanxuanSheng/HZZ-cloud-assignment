# HZZ-cloud-assignment
docker compose version:
```
cd local-laptop
docker build -t producer -f Dockerfile.producer .
docker build -t consumer -f Dockerfile.consumer .
docker build -t drawplot -f Dockerfile.drawplot .
docker-compose up -d
docker ps
```
check the ports of nginx default http://localhost:8080/result.pdf


Kubernetes version：
```
cd Kubernetes
docker build -t producer -f Dockerfile.producer .
docker build -t consumer -f Dockerfile.consumer .
docker build -t drawplot -f Dockerfile.drawplot .

kubectl apply -f PVC.yaml
kubectl apply -f HZZ-final.yaml

kubectl get svc
```
webserver-service   NodePort    10.100.112.118   <none>        8080:*****/TCP       62s
http://localhost:*****/result.pdf
