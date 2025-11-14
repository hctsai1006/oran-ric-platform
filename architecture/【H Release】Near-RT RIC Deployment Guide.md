
:::info
1. Hardware requests：
	- RAM：20G RAM
	- CPU：8 core
	- Disk：60GB
    - Ubuntu 20.04 LTS (Focal Fossa)
:::

## 1. Install the Docker, Kubernetes and Helm 3
### **1.1 Open terminate (Ctrl+Alt+T)**
### **1.2 Become root user：**
==Note：== All the commands need to be executed as root.
```javascript=
sudo -i
```
![](https://hackmd.io/_uploads/BJfsMIqKh.png)

### **1.3 Install the Dependent Tools**
```javascript=
apt-get update
apt-get install -y git vim curl net-tools openssh-server python3-pip nfs-common
```
![](https://i.imgur.com/rjEIHjr.png)
![](https://i.imgur.com/KMa8Paf.png)
### **1.4 Download the source code of RIC Platform**
```javascript=
cd ~
git clone https://gerrit.o-ran-sc.org/r/ric-plt/ric-dep -b h-release
```
URL: https://gerrit.o-ran-sc.org/r/gitweb?p=ric-plt%2Fric-dep.git;a=shortlog;h=refs%2Fheads%2Fg-release
![](https://i.imgur.com/ymYAukT.png)

### **1.5 Execute the Installation Script of the Docker, Kubernetes and Helm 3**
:::info
If you want to change the version, you should use this command:
```javascript=
cd ric-dep/bin
vim install_k8s_and_helm.sh
```
:::
```javascript=
cd ric-dep/bin
./install_k8s_and_helm.sh
```
![](https://hackmd.io/_uploads/By7GgIqFn.png)


### **1.6 Check the Status of Kubernetes deployment**
```javascript=
kubectl get pods -A
```
![](https://i.imgur.com/tvkNIJl.png)
### **1.7 Check the version of Docker, Kubernetes and Helm**
|            | version  | command         |
| ---------- | -------- | --------------- |
| Helm       | 3.5.4    | helm version    |
| Kubernetes | 1.16.0   | kubectl version |
| Kubecniv           |    0.7.5      |  kubectl version               |
| Docker     | 20.10.21 | docker version  |



## 2. Install the Near-RT RIC Platform
### **2.1 Add the ric-common templates**
==Note:== In the D and E version, 2.1 is in the `./deploy-ric-platform ../RECIPE_EXAMPLE/PLATFORM/example_recipe_oran_dawn_release.yaml` script file to install.
```javascript=
./install_common_templates_to_helm.sh
```
![](https://i.imgur.com/IcgDqOt.png)
==NOTE:== How many '`servecm not yet running. sleeping for 2 seconds`' it is depends on your download speed. Because it will wait to download [download chartmuseum](https://s3.amazonaws.com/chartmuseum/release/latest/bin/linux/amd64/chartmuseum).
```javascript=
./setup-ric-common-template
```
![](https://i.imgur.com/1lz0Bu2.png)

## **[2.2 Edit Deployment Configuration](https://hackmd.io/@2xIzdkQiS9K3Pfrv6tVEtA/Bkzlwdzci)**
## **2.3 Install nfs for InfluxDB**
```javascript=
kubectl create ns ricinfra
helm repo add stable https://charts.helm.sh/stable
helm install nfs-release-1 stable/nfs-server-provisioner --namespace ricinfra 
kubectl patch storageclass nfs -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
sudo apt install nfs-common
```
## **2.4 Execute the Installation Script of Near-RT RIC**
**Find your IP of VM：**
```javascript=
ip a
```
![](https://i.imgur.com/ALgQCgF.png)
**Modify the IP of RIC and AUX：**
```javascript=
vim ~/ric-dep/RECIPE_EXAMPLE/example_recipe_oran_h_release.yaml
```
![](https://i.imgur.com/uQhKVOi.png)
**Deploy the RIC Platform：**
```javascript=
cd ~/ric-dep/bin
./install -f ../RECIPE_EXAMPLE/example_recipe_oran_h_release.yaml -c "jaegeradapter influxdb"
```
![](https://i.imgur.com/W8ifnTd.png)
### **2.5 Check the Status of Near-RT RIC deployment**
- Results similar to the output shown below indicate a complete and successful deployment, all are either **“Completed”** or **“Running”**, and that none are **“Error”**, **“Pending”**, **“Evicted”**,or **“ImagePullBackOff”**.
- The status of pods “**PodInitializing”** & **“Init”** & **“ContainerCreating”** mean that the pods are creating now, you need to wait for deploying.
```javascript=
kubectl get pods -A
```
![](https://hackmd.io/_uploads/ByHPkL5Kn.png)

- **If inflexdb2 is pending, you can refer Issues 1.**
- **If tiller is Error,you can skip it.**

## 3. Install the DMS Tool
### 3.1 Install the Chartmuseum for DMS Tool
**Customized Setting：**
```javascript=
cd ~
echo "env:
  open:
    STORAGE: local
    CONTEXT_PATH: /charts
    DISABLE_API: false
persistence:
  enabled: true
  accessMode: ReadWriteOnce
  size: 8Gi
  storageClass: nfs
service:
  type: NodePort" > chart.yaml
```
![](https://i.imgur.com/40Scs41.png)
**Install Chatmuseum：**
```javascript=
helm install r4-chartmuseum stable/chartmuseum -f chart.yaml --namespace ricinfra
```
![](https://i.imgur.com/LW5rfFD.png)

**Verify the IP and Port：**
```javascript=
export NODE_PORT=$(sudo kubectl get --namespace ricinfra -o jsonpath="{.spec.ports[0].nodePort}" services r4-chartmuseum-chartmuseum)
export NODE_IP=$(sudo kubectl get nodes --namespace ricinfra -o jsonpath="{.items[0].status.addresses[0].address}")
echo http://$NODE_IP:$NODE_PORT/
```
![](https://i.imgur.com/lH2Nnu9.png)

### 3.2 Install the DMS tool
**Prepare source code：**
```javascript=
docker run --rm -u 0 -it -d -p 8080:8080 -e DEBUG=1 -e STORAGE=local -e STORAGE_LOCAL_ROOTDIR=/chart -v $(pwd)/charts:/charts chartmuseum/chartmuseum:latest
export CHART_REPO_URL=http://0.0.0.0:8090
git clone https://gerrit.o-ran-sc.org/r/ric-plt/appmgr -b h-release
```
![](https://i.imgur.com/uuaTdFJ.png)

**Install DMS tool：**
```javascript=
cd appmgr/xapp_orchestrater/dev/xapp_onboarder
apt-get install python3-pip
pip3 uninstall xapp_onboarder
pip3 install ./
chmod 755 /usr/local/bin/dms_cli
ls -la /usr/local/lib/python3.8
chmod -R 755 /usr/local/lib/python3.8
```
![](https://i.imgur.com/ugWMbbs.png)

## Appendix

### Issues of InfluxDB & NFS
**Issue 1：Pod is Crashbackoff**

```javascript=
Warning FailedMount 110s kubelet MountVolume.SetUp failed for volume "pvc-759e2292-6938-4b8e-b6e3-67bbf9b7b904" : mount failed: exit status 32
```

- Solution：Re-install the dependent tools
```javascript=
apt-get install -y nfs-common
```
**Issue 2：Unauthorized**

- If the xApp need to access the InfluxDB, it maybe need to login-in by using user/password
```javascript=
Error: raise InfluxDBClientError(err_msg, response.status_code) influxdb.exceptions.InfluxDBClientError: 401: {"code":"unauthorized","message":"Unauthorized"}
```
- Solution：Modify the user/password in the xApp code
Step 1：Enter the secret of InfluxDB
```javascript=
kubectl get secret -n ricplt
kubectl edit secret -n ricplt <InfluxDB secret>
```
Step 2：Decode the user/password
```javascript=
echo 'amYzOTJoZjc4MmhmOTMyaAo=' | base64 --decode
```
Step 3：Modify the InfluxDB user/password in the xApp using the decoded user/password


### Clear the k8s
https://ithelp.ithome.com.tw/articles/10262330
### Delete the pod
```javascript=
kubectl delete pod --all -n <namespace>
```

### Uninstall Near-RT RIC Platform
```javascript=
cd ~/ric-dep/bin
./uninstall
```

### Script to Deploy RIC Platform quickly
```javascript=
sudo -i
touch Deploy_RIC-Platform_H-Release.sh
chmod +x Deploy_RIC-Platform_H-Release.sh
vim Deploy_RIC-Platform_H-Release.sh
```
```javascript=
# Install the Dependent Tools
#-------------------------------------------------------------------------------
echo "------------------ Install the Dependent Tools ----------------------"
apt-get update
apt-get install -y git vim curl net-tools openssh-server python3-pip nfs-common

# Download the source code of RIC Platform
#-------------------------------------------------------------------------------
echo "------------ Download the source code of RIC Platform ---------------"
cd ~
git clone https://gerrit.o-ran-sc.org/r/ric-plt/ric-dep -b h-release

# Execute the Installation Script of the Docker, Kubernetes and Helm 3
#-------------------------------------------------------------------------------
echo "--------------Install Docker, Kubernetes and Helm 3------------------"
cd ric-dep/bin
./install_k8s_and_helm.sh

# Add the ric-common templates
#-------------------------------------------------------------------------------
echo "--------------------Install the Dependent Tools----------------------"
./install_common_templates_to_helm.sh
./setup-ric-common-template
cd ../..

# Install nfs for InfluxDB
#-------------------------------------------------------------------------------
echo "------------------Install the Dependent Tools------------------------"
kubectl create ns ricinfra
helm repo add stable https://charts.helm.sh/stable
helm install nfs-release-1 stable/nfs-server-provisioner --namespace ricinfra 
kubectl patch storageclass nfs -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
sudo apt install nfs-common

# Deploy the RIC Platform
echo "------------------Install the Dependent Tools------------------------"
cd ~/ric-dep/bin
./install -f ../RECIPE_EXAMPLE/example_recipe_oran_h_release.yaml -c "jaegeradapter influxdb"
kubectl get pods -A
cd ../..

echo "----------wait:30s---------"
for i in 10 20 30
do
    echo "----------$i s---------"
    sleep 10
done

# check the bug of influxdb
echo "-------------------------check the influxdb--------------------------"
z=$(kubectl get pods -n ricplt | grep "influxdb" | awk '{print $3}')
if [ $z = "Running" ]
then
    echo "------->already Running"
else
    echo "------->still Pending"
    cd ~
    echo "apiVersion: v1
kind: PersistentVolume
metadata:
  name: r4-influxdb
  labels:
    name: r4-influxdb
spec:
  storageClassName: nfs
  capacity:
    storage: 50Gi
  accessModes:
    - ReadWriteOnce
  hostPath:
    type: DirectoryOrCreate
    path: /mnt/ricplt-influxdb-data" > influxdb-pv.yaml

    kubectl apply -f influxdb-pv.yaml
fi

echo "----------wait:30s---------"
for i in 10 20 30
do
    echo "----------$i s---------"
    sleep 10
done

# Install the DMS Tool
echo "-------------------------Install the DMS Tool--------------------------"
cd ~
echo "env:
  open:
    STORAGE: local
    CONTEXT_PATH: /charts
    DISABLE_API: false
persistence:
  enabled: true
  accessMode: ReadWriteOnce
  size: 8Gi
  storageClass: nfs
service:
  type: NodePort" > chart.yaml

helm install r4-chartmuseum stable/chartmuseum -f chart.yaml --namespace ricinfra
export NODE_PORT=$(kubectl get --namespace ricinfra -o jsonpath="{.spec.ports[0].nodePort}" services r4-chartmuseum-chartmuseum)
export NODE_IP=$(kubectl get nodes --namespace ricinfra -o jsonpath="{.items[0].status.addresses[0].address}")
echo http://$NODE_IP:$NODE_PORT/

docker run --rm -u 0 -it -d -p 8090:8080 -e DEBUG=1 -e STORAGE=local -e STORAGE_LOCAL_ROOTDIR=/chart -v $(pwd)/charts:/charts chartmuseum/chartmuseum:latest
export CHART_REPO_URL=http://0.0.0.0:8090
git clone https://gerrit.o-ran-sc.org/r/ric-plt/appmgr -b h-release
cd appmgr/xapp_orchestrater/dev/xapp_onboarder
apt-get install python3-pip
pip3 uninstall xapp_onboarder
pip3 install ./
chmod 755 /usr/local/bin/dms_cli
ls -la /usr/local/lib/ptyhon3.8
chmod -R 755 /usr/local/lib/python3.8
```
```javascript=
./Deploy_RIC-Platform_H-Release.sh
```
[GIT LAB](https://github.com/tobby-yuan/ric_install.git)
## Issues 
### 1. r4-influxdb-influxdb2-0 is Pending
![](https://i.imgur.com/FD17tVp.png)
:::info
**- reason**
```javascript=
kubectl describe pods -n ricplt r4-influxdb-influxdb2-0
```
![](https://i.imgur.com/WLAQAOL.png)
```javascript=
kubectl get pvc -A
```
![](https://i.imgur.com/hjOn7Ie.png)
- We can found that influxdb was pending, so its pod was pending 
```javascript=
kubectl describe pods -n ricplt r4-influxdb-influxdb2-0
```
![](https://i.imgur.com/GoBSnst.png)
- We can found that we didn't give it a volume.
```javascript=
kubectl get pv -A
```
![](https://i.imgur.com/UEAk5Ow.png)
- We can found that we really didn't give it a volume.
:::
:::success
**- solution**
```javascript=
cd ~
echo "apiVersion: v1
kind: PersistentVolume
metadata:
  name: r4-influxdb
  labels:
    name: r4-influxdb-influxdb2
spec:
  storageClassName: "nfs"
  capacity:
    storage: 50Gi
  accessModes:
    - ReadWriteOnce
  hostPath:
    type: DirectoryOrCreate
    path: /mnt/ricplt-influxdb-data" > influxdb-pv.yaml

kubectl apply -f influxdb-pv.yaml
```
![](https://i.imgur.com/Xn2uAdP.png)
![](https://i.imgur.com/xEespvY.png)
![](https://i.imgur.com/3Wslf1n.png)

:::
### 2. Change the DMS Install(2023/2/2)
- It have some problem about authorized
- original
```javascript=
git clone https://gerrit.o-ran-sc.org/r/ric-plt/appmgr -b h-release
cd ~/appmgr/xapp_orchestrater/dev/xapp_onboarder
pip3 install ./
```
- Change
```javascript=
docker run --rm -u 0 -it -d -p 8090:8080 -e DEBUG=1 -e STORAGE=local -e STORAGE_LOCAL_ROOTDIR=/chart -v $(pwd)/charts:/charts chartmuseum/chartmuseum:latest
export CHART_REPO_URL=http://0.0.0.0:8090
git clone https://gerrit.o-ran-sc.org/r/ric-plt/appmgr -b h-release
cd appmgr/xapp_orchestrater/dev/xapp_onboarder
apt-get install python3-pip
pip3 uninstall xapp_onboarder
pip3 install ./
chmod 755 /usr/local/bin/dms_cli
ls -la /usr/local/lib/ptyhon3.8
chmod -R 755 /usr/local/lib/python3.8
```

### 3. Can't install docker
:::info
- When I ran this command `./install_k8s_and_helm.sh`, it appeared this error
![](https://i.imgur.com/esghmWn.png)
- Can't find this docker version 20.10.12-0ubuntu2~20.04.1
- Command ` apt-get install -y --allow-downgrades --allow-change-held-packages --allow-unauthenticated --ignore-hold docker.io=20.10.12-0ubuntu2~20.04.1`
- error
```shell
Reading package lists... Done
Building dependency tree
Reading state information... Done
E: Version '20.10.12-0ubuntu2~20.04.1' for 'docker.io' was not found
```
:::

:::success
- **solution**
- Install master version
```javascript=
git clone https://gerrit.o-ran-sc.org/r/ric-plt/ric-dep -b master
```
- Because the version of docker becomes 20.10.12-0ubuntu1~20.04.1 
:::


### 4. E2term fail
:::info
- If you install this [branch](https://gerrit.o-ran-sc.org/r/gitweb?p=ric-plt/ric-dep.git;a=tree;h=0ad067633243c09b6f79d80d4bc51f56867fffa1;hb=0ad067633243c09b6f79d80d4bc51f56867fffa1)(or above) and [Improve E2term's log-level](https://hackmd.io/@2xIzdkQiS9K3Pfrv6tVEtA/Bkzlwdzci#41-Modify-the-Log-Level), it will occur an error
![](https://i.imgur.com/qGjH5CZ.png)
:::
:::success
- **solution**
- Don't revise this file `vim ~/ric-dep/helm/e2term/templates/deployment.yaml`, because this branch already improve the log-level.
:::
