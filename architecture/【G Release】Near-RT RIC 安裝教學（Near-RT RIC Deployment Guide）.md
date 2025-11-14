# 【G Release】Near-RT RIC Deployment Guide
:::info
1. Hardware requests：
	- RAM：8G RAM
	- CPU：6 core
	- Disk：40G Storage
2. Installation Environment：
	- Host：Windows 10
	- Hypervisor：VMware Workstation 16 Player
	- VM：Ubuntu 20.04 LTS (Focal Fossa)
:::

## 1. Install the Docker, Kubernetes and Helm 3
### **1.1 Open terminate (Ctrl+Alt+T)**
### **1.2 Become root user：**
==Note：== All the commands need to be executed as root.
```javascript=
sudo -i
```
![](https://i.imgur.com/ZOPXGZM.png)
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
git clone https://gerrit.o-ran-sc.org/r/ric-plt/ric-dep -b g-release
```
URL: https://gerrit.o-ran-sc.org/r/gitweb?p=ric-plt%2Fric-dep.git;a=shortlog;h=refs%2Fheads%2Fg-release
![](https://i.imgur.com/ymYAukT.png)

### **1.5 Execute the Installation Script of the Docker, Kubernetes and Helm 3**
```javascript=
cd ric-dep/bin
./install_k8s_and_helm.sh
```
![](https://i.imgur.com/AXSpjG9.png)

### **1.6 Check the Status of Kubernetes deployment**
```javascript=
kubectl get pods -A
```
![](https://i.imgur.com/tvkNIJl.png)
### **1.7 Check the version of Docker, Kubernetes and Helm**
|            | version  | command        |
| ---------- | -------- | -------------- |
| Helm       | 3.5.4    | helm version   |
| Kubernetes | 1.16.0   | kubectl version |
| Docker     | 20.10.12 | docker version |

![](https://i.imgur.com/L3TczOC.png)

## 2. Install the Near-RT RIC Platform
### **2.1 Add the ric-common templates**
==Note:== In the D and E version, 2.1 is in the `./deploy-ric-platform ../RECIPE_EXAMPLE/PLATFORM/example_recipe_oran_dawn_release.yaml` script file to install.
```javascript=
./install_common_templates_to_helm.sh
```
![](https://i.imgur.com/IcgDqOt.png)
==NOTE:== How many &#39;`servecm not yet running. sleeping for 2 seconds`&#39; it is depends on your download speed. Because it will wait to download [download chartmuseum](https://s3.amazonaws.com/chartmuseum/release/latest/bin/linux/amd64/chartmuseum).
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
kubectl patch storageclass nfs -p &#39;{&#34;metadata&#34;: {&#34;annotations&#34;:{&#34;storageclass.kubernetes.io/is-default-class&#34;:&#34;true&#34;}}}&#39;
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
vim ~/ric-dep/RECIPE_EXAMPLE/example_recipe_oran_g_release.yaml
```
![](https://i.imgur.com/uQhKVOi.png)
**Deploy the RIC Platform：**
```javascript=
cd ~/ric-dep/bin
./install -f ../RECIPE_EXAMPLE/example_recipe_oran_g_release.yaml -c &#34;jaegeradapter influxdb&#34;
```
![](https://i.imgur.com/W8ifnTd.png)
### **2.5 Check the Status of Near-RT RIC deployment**
- Results similar to the output shown below indicate a complete and successful deployment, all are either **“Completed”** or **“Running”**, and that none are **“Error”**, **“Pending”**, **“Evicted”**,or **“ImagePullBackOff”**.
- The status of pods “**PodInitializing”** &amp; **“Init”** &amp; **“ContainerCreating”** mean that the pods are creating now, you need to wait for deploying.
```javascript=
kubectl get pods -A
```
![](https://i.imgur.com/Zzt5cY0.png)
- **If inflexdb2 is pending, you can refer Issues 1.**

## 3. Install the DMS Tool
### 3.1 Install the Chartmuseum for DMS Tool
**Customized Setting：**
```javascript=
cd ~
echo &#34;env:
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
  type: NodePort&#34; &gt; chart.yaml
```
![](https://i.imgur.com/40Scs41.png)
**Install Chatmuseum：**
```javascript=
helm install r4-chartmuseum stable/chartmuseum -f chart.yaml --namespace ricinfra
```
![](https://i.imgur.com/LW5rfFD.png)

**Verify the IP and Port：**
```javascript=
export NODE_PORT=$(kubectl get --namespace ricinfra -o jsonpath=&#34;{.spec.ports[0].nodePort}&#34; services r4-chartmuseum-chartmuseum)
export NODE_IP=$(kubectl get nodes --namespace ricinfra -o jsonpath=&#34;{.items[0].status.addresses[0].address}&#34;)
echo http://$NODE_IP:$NODE_PORT/
```
![](https://i.imgur.com/lH2Nnu9.png)

### 3.2 Install the DMS tool
**Prepare source code：**
```javascript=
docker run --rm -u 0 -it -d -p 8090:8080 -e DEBUG=1 -e STORAGE=local -e STORAGE_LOCAL_ROOTDIR=/chart -v $(pwd)/charts:/charts chartmuseum/chartmuseum:latest
export CHART_REPO_URL=http://0.0.0.0:8090
```
```javascript=
git clone https://gerrit.o-ran-sc.org/r/ric-plt/appmgr -b g-release
```
![](https://i.imgur.com/uuaTdFJ.png)

**Install DMS tool：**
```javascript=
cd appmgr/xapp_orchestrater/dev/xapp_onboarder
apt-get install python3-pip
pip3 uninstall xapp_onboarder
pip3 install ./
chmod 755 /usr/local/bin/dms_cli
ls -la /usr/local/lib/ptyhon3.8
chmod -R 755 /usr/local/lib/python3.8
```
![](https://i.imgur.com/ugWMbbs.png)

## Appendix
### Uninstall Near-RT RIC Platform
```javascript=
cd ~/ric-dep/bin
helm uninstall r4-chartmuseum --namespace ricinfra
./uninstall
```

### [E2 Manager vesion revision](https://hackmd.io/@Kenny-Lai/SkZCi4vC3#1-2-Version)

### [Vespa image revision](https://hackmd.io/NkUw-oaWQdaVN3rogOOO6g)

### [InfluxDB v2 Setting](https://hackmd.io/@2xIzdkQiS9K3Pfrv6tVEtA/G-release_TS_USE_CASE#6-InfluxDB-v2-Setting)

### [Prometheus Setting](https://hackmd.io/@Kenny-Lai/rJ6hIGEK2#Integrate-with-Prometheus-Server-of-Near-RT-RIC-Platform)

### Script to Deploy RIC Platform quickly
```javascript=
sudo -i
touch Deploy_RIC-Platform_G-Release.sh
chmod +x Deploy_RIC-Platform_G-Release.sh
vim Deploy_RIC-Platform_G-Release.sh
```
```javascript=
# Install the Dependent Tools
#-------------------------------------------------------------------------------
echo &#34;------------------ Install the Dependent Tools ----------------------&#34;
apt-get update
apt-get install -y git vim curl net-tools openssh-server python3-pip nfs-common

# Download the source code of RIC Platform
#-------------------------------------------------------------------------------
echo &#34;------------ Download the source code of RIC Platform ---------------&#34;
cd ~
git clone https://gerrit.o-ran-sc.org/r/ric-plt/ric-dep -b g-release

# Execute the Installation Script of the Docker, Kubernetes and Helm 3
#-------------------------------------------------------------------------------
echo &#34;--------------Install Docker, Kubernetes and Helm 3------------------&#34;
cd ric-dep/bin
./install_k8s_and_helm.sh

# Add the ric-common templates
#-------------------------------------------------------------------------------
echo &#34;--------------------Install the Dependent Tools----------------------&#34;
./install_common_templates_to_helm.sh
./setup-ric-common-template
cd ../..

# Install nfs for InfluxDB
#-------------------------------------------------------------------------------
echo &#34;------------------Install the Dependent Tools------------------------&#34;
kubectl create ns ricinfra
helm repo add stable https://charts.helm.sh/stable
helm install nfs-release-1 stable/nfs-server-provisioner --namespace ricinfra 
kubectl patch storageclass nfs -p &#39;{&#34;metadata&#34;: {&#34;annotations&#34;:{&#34;storageclass.kubernetes.io/is-default-class&#34;:&#34;true&#34;}}}&#39;
sudo apt install nfs-common

# Deploy the RIC Platform
echo &#34;------------------Install the Dependent Tools------------------------&#34;
cd ~/ric-dep/bin
./install -f ../RECIPE_EXAMPLE/example_recipe_oran_g_release.yaml -c &#34;jaegeradapter influxdb&#34;
kubectl get pods -A
cd ../..

echo &#34;----------wait:30s---------&#34;
for i in 10 20 30
do
    echo &#34;----------$i s---------&#34;
    sleep 10
done

# check the bug of influxdb
echo &#34;-------------------------check the influxdb--------------------------&#34;
z=$(kubectl get pods -n ricplt | grep &#34;influxdb&#34; | awk &#39;{print $3}&#39;)
if [ $z = &#34;Running&#34; ]
then
    echo &#34;-------&gt;already Running&#34;
else
    echo &#34;-------&gt;still Pending&#34;
    cd ~
    echo &#34;apiVersion: v1
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
    path: /mnt/ricplt-influxdb-data&#34; &gt; influxdb-pv.yaml

    kubectl apply -f influxdb-pv.yaml
fi

echo &#34;----------wait:30s---------&#34;
for i in 10 20 30
do
    echo &#34;----------$i s---------&#34;
    sleep 10
done

# Install the DMS Tool
echo &#34;-------------------------Install the DMS Tool--------------------------&#34;
cd ~
echo &#34;env:
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
  type: NodePort&#34; &gt; chart.yaml

helm install r4-chartmuseum stable/chartmuseum -f chart.yaml --namespace ricinfra
export NODE_PORT=$(kubectl get --namespace ricinfra -o jsonpath=&#34;{.spec.ports[0].nodePort}&#34; services r4-chartmuseum-chartmuseum)
export NODE_IP=$(kubectl get nodes --namespace ricinfra -o jsonpath=&#34;{.items[0].status.addresses[0].address}&#34;)
echo http://$NODE_IP:$NODE_PORT/

docker run --rm -u 0 -it -d -p 8090:8080 -e DEBUG=1 -e STORAGE=local -e STORAGE_LOCAL_ROOTDIR=/chart -v $(pwd)/charts:/charts chartmuseum/chartmuseum:latest
export CHART_REPO_URL=http://0.0.0.0:8090
git clone https://gerrit.o-ran-sc.org/r/ric-plt/appmgr -b g-release
cd appmgr/xapp_orchestrater/dev/xapp_onboarder
apt-get install python3-pip
pip3 uninstall xapp_onboarder
pip3 install ./
chmod 755 /usr/local/bin/dms_cli
ls -la /usr/local/lib/ptyhon3.8
chmod -R 755 /usr/local/lib/python3.8
```
```javascript=
./Deploy_RIC-Platform_G-Release.sh
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
- We can found that we didn&#39;t give it a volume.
```javascript=
kubectl get pv -A
```
![](https://i.imgur.com/UEAk5Ow.png)
- We can found that we really didn&#39;t give it a volume.
:::
:::success
**- solution**
```javascript=
cd ~
echo &#34;apiVersion: v1
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
    path: /mnt/ricplt-influxdb-data&#34; &gt; influxdb-pv.yaml

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
git clone https://gerrit.o-ran-sc.org/r/ric-plt/appmgr -b g-release
cd ~/appmgr/xapp_orchestrater/dev/xapp_onboarder
pip3 install ./
```
- Change
```javascript=
docker run --rm -u 0 -it -d -p 8090:8080 -e DEBUG=1 -e STORAGE=local -e STORAGE_LOCAL_ROOTDIR=/chart -v $(pwd)/charts:/charts chartmuseum/chartmuseum:latest
export CHART_REPO_URL=http://0.0.0.0:8090
git clone https://gerrit.o-ran-sc.org/r/ric-plt/appmgr -b g-release
cd appmgr/xapp_orchestrater/dev/xapp_onboarder
apt-get install python3-pip
pip3 uninstall xapp_onboarder
pip3 install ./
chmod 755 /usr/local/bin/dms_cli
ls -la /usr/local/lib/ptyhon3.8
chmod -R 755 /usr/local/lib/python3.8
```

### 3. Can&#39;t install docker(2023/3/27)
:::info
- When I ran this command `./install_k8s_and_helm.sh`, it appeared this error
![](https://i.imgur.com/esghmWn.png)
- Can&#39;t find this docker version 20.10.12-0ubuntu2~20.04.1
- Command ` apt-get install -y --allow-downgrades --allow-change-held-packages --allow-unauthenticated --ignore-hold docker.io=20.10.12-0ubuntu2~20.04.1`
- error
```shell
Reading package lists... Done
Building dependency tree
Reading state information... Done
E: Version &#39;20.10.12-0ubuntu2~20.04.1&#39; for &#39;docker.io&#39; was not found
```
:::

:::success
- **solution**
- Install master version
```javascript=
git clone https://gerrit.o-ran-sc.org/r/ric-plt/ric-dep -b master
```
- Because the version of docker becomes 20.10.21-0ubuntu1~20.04.2
:::


### 4. E2term fail(2023/4/14)
:::info
- If you install this [branch](https://gerrit.o-ran-sc.org/r/gitweb?p=ric-plt/ric-dep.git;a=tree;h=0ad067633243c09b6f79d80d4bc51f56867fffa1;hb=0ad067633243c09b6f79d80d4bc51f56867fffa1)(or above) and [Improve E2term&#39;s log-level](https://hackmd.io/@2xIzdkQiS9K3Pfrv6tVEtA/Bkzlwdzci#41-Modify-the-Log-Level), it will occur an error
![](https://i.imgur.com/qGjH5CZ.png)
:::
:::success
- **solution**
- Don&#39;t revise this file `vim ~/ric-dep/helm/e2term/templates/deployment.yaml`, because this branch already improve the log-level.
:::

### 5. Chartmuseum fail(2023/7/7)
:::info
![](https://hackmd.io/_uploads/H1Po9-HFh.png)
- Servecm can download chartmuseum binary, but the hardcoded location does not work anymore
- So, we download it now before starting servecm, so that it&#39;s available when servecm tries to start the chartmuseum binary
:::
:::success
- **solution**
```shell=
vim ~/ric-dep/bin/install_common_templates_to_helm.sh
```
- Add line 8 to 14
```shell=
...
echo &#34;Installing servecm (Chart Manager) and common templates to helm3&#34;

helm plugin install https://github.com/jdolitsky/helm-servecm
eval $(helm env |grep HELM_REPOSITORY_CACHE)
echo ${HELM_REPOSITORY_CACHE}

# servecm can download chartmuseum binary, but the hardcoded location does not work anymore
# so, we download it now before starting servecm, so that it&#39;s available when servecm
# tries to start the chartmuseum binary
curl -LO https://get.helm.sh/chartmuseum-v0.15.0-linux-386.tar.gz
tar xzvf chartmuseum-v0.15.0-linux-386.tar.gz
chmod +x ./linux-386/chartmuseum
cp ./linux-386/chartmuseum /usr/local/bin

nohup helm servecm --port=8879 --context-path=/charts --storage local --storage-local-rootdir $HELM_REPOSITORY_CACHE/local/ &lt;&lt;EOF &amp;
yes
EOF
...
```
:::

### 6. cgroup issue
:::danger
```shell=
[kubelet-check] The HTTP call equal to &#39;curl -sSL http://localhost:10248/healthz&#39; failed with error: Get http://localhost:10248/healthz: dial tcp 127.0.0.1:10248: connect: connection refused.

Unfortunately, an error has occurred:
        timed out waiting for the condition

This error is likely caused by:
        - The kubelet is not running
        - The kubelet is unhealthy due to a misconfiguration of the node in some way (required cgroups disabled)

If you are on a systemd-powered system, you can try to troubleshoot the error with the following commands:
        - &#39;systemctl status kubelet&#39;
        - &#39;journalctl -xeu kubelet&#39;

Additionally, a control plane component may have crashed or exited when started by the container runtime.
To troubleshoot, list all containers using your preferred container runtimes CLI, e.g. docker.
Here is one example how you may list all Kubernetes containers running in docker:
        - &#39;docker ps -a | grep kube | grep -v pause&#39;
        Once you have found the failing container, you can inspect its logs with:
        - &#39;docker logs CONTAINERID&#39;
error execution phase wait-control-plane: couldn&#39;t initialize a Kubernetes cluster
To see the stack trace of this error execute with --v=5 or higher
+ cd /root
+ rm -rf .kube

```
:::

### 7. [DNS issue](https://hackmd.io/@Jerry0714/Hk6MyGiph#7-Revise-nameserver-resolvedconf-to-the-8888)