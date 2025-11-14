# KPM xApp (For Slice) User Guide 

:::success
**Intro**:
In the G release, O-DU only finish the setup, subscription and indication message of E2AP. The indication message doesn't finish so that O-DU can't report the measurement to xApp.

Moreover, KPM xApp should modified the field to match with O-DU, and KPM can receive and store the measurement in the database.

It's the user guide to execute the modified O-DU and KPM xApp to report the indication. 

**Goal:**
- KPM xApp subscribes the metrics from O-DU.
- KPM xApp stores the metrics in influxDB of RIC
- O-DU reports the metrics depends on subscription from KPM xApp

:::

[TOC]

## 1. Summary
The KPM (Key Performance Management) xApp of O-RAN is a software application designed to provide real-time monitoring and analysis of network performance in a 5G O-RAN (Open Radio Access Network) environment.

This KPM xApp primarily provide the measurment for Slice xApp to configure the slice level, thus this xApp should support the measurement item which Slice xApp needs. 


### MSC
It's the MSC showing the procedure. The final result follow these steps:
![](https://hackmd.io/_uploads/BJuhsRHsh.png)



### Report measurments
O-DU supports KPM xApp subscribes these measurements:

- Cell measurement: The UE measurement per cell transmits in Indication Message Format 1. Label infos are:
    - Average DL UE throughput in gNB (DRB.UEThpDl)
    - Mean DL PRB used for data traffic (RRU.PrbUsedDl)
    - DL total available PRB (RRU.PrbAvailDl)
    - DL Total PRB Usage (RRU.PrbTotDl)
- Slice mesaurement The UE measurement per slice transmits in Indication Message Format 3. Label infos are:
    - Average DL UE throughput in slice (DRB.UEThpDl.SNSSAI)
    - Mean DL PRB used for data traffic (RRU.PrbUsedDl.SNSSAI)

### Environment
![](https://i.imgur.com/3KFTVHr.png)

**RIC Platform** 
- Repository: https://gerrit.o-ran-sc.org/r/ric-plt/ric-dep
- Version: F Release

**KPM xApp**
- Repository: https://github.com/jackychiangtw/kpm-xapp
- Version: master

**O-DU High**
- Repository: https://github.com/jackychiangtw/odu-bmwlab.git
- Version: sch_slice_based
- Date: 

![](https://hackmd.io/_uploads/SJ9Ruiesh.png)

## 2. Modify KPM xApp

KPM xApp uses the database - influxDB in the RIC platfrom, to store the measurements. However, influxDB may enable the authentication so that KPM xApp should pass the authentication to store the measurements.

### 2.1 Get the Authentication Information

1. Enter the secret of InfluxDB
```bash=
kubectl get secret -n ricplt
kubectl edit secret -n ricplt <InfluxDB secret>
```
-n ricplt：此-n標誌指定秘密所在的命名空間。在本例中，它被命名為ricplt
在這邊這個 <InfluxDB secret> 就是 r4-influxdb-influxdb2-auth
所以整條命令會像是：
kubectl edit secret -n ricplt r4-influxdb-influxdb2-auth

Updating Secrets
You can edit the value of secrets using the kubectl edit command:



![](https://hackmd.io/_uploads/Hymj6Zcj3.png)

2. The user/password would be printed. Record it.
3. Decode the user/password
```bash=
echo 'amYzOTJoZjc4MmhmOTMyaAo=' | base64 --decode
```
![](https://hackmd.io/_uploads/SJVsyGqin.png)

### 2.2 Modify the Authentication Information in KPM xApp Source code

```bash=
cd control
vim control.go
```

Modify the username/password in line 39:
![](https://hackmd.io/_uploads/B13i1Mcj3.png)


## 3. Installation
Follow the steps below to finish the installation

### 3.1 Install RIC Platform

Follow this [user guide](https://hackmd.io/@Min-xiang/SJD9Xh5c9) to install RIC Platform.

### 3.2 Install KPM xApp

**Compile the Images and Onboard the Container**

In the environment which installed RIC platform, follow the steps below to install KPM xApp:

- Import charts url for `dms_cli`
```bash=
export NODE_PORT=$(sudo kubectl get --namespace ricinfra -o jsonpath="{.spec.ports[0].nodePort}" services r4-chartmuseum-chartmuseum)
export NODE_IP=$(sudo kubectl get nodes --namespace ricinfra -o jsonpath="{.items[0].status.addresses[0].address}")
export CHART_REPO_URL=http://$NODE_IP:$NODE_PORT/charts
```
- Onboard and install the KPM xApp.
```=
cd kpm
docker build . -t docker.io/mb8746/kpm:1.0.0
cd config/
dms_cli uninstall kpm ricxapp
dms_cli onboard config-file.json schema.json 
dms_cli install kpm 1.0.0 ricxapp
```
- Check if is installed successfully
```bash=
kubectl get pods -A
```
![](https://i.imgur.com/XePnS8V.jpg)

### 3.3 Compile O-DU
**Install the required libraries**
:::info
Update newest package.
```shell=
sudo apt-get update

## If you can't use `ifconfig`, run below command to install tools.
sudo apt-get install net-tools -y
```

Install required libraries to build & compile O-DU high.
```shell=
## GCC, make sure your GCC version is 4.6.3 or above for compiling, and install it if necessary.
gcc --version
## Install GCC by below command
sudo apt-get install -y build-essential

## LKSCTP
sudo apt-get install -y libsctp-dev

## PCAP 
sudo apt-get install -y libpcap-dev
```
:::

**Config the DU, RIC and CU_Stub Address**

Check the E2 termination sctp port in K8S. The rule is internal:external port. 

![](https://i.imgur.com/6bjcfMQ.png)
> External port: 32222

Modify RIC IP in `du_cfg.h`:
```bash=
vim l2/src/du_app/du_cfg.h 
```

At line 33:

![](https://i.imgur.com/KsP4YCy.png)
:::info
- DU Address: O-DU's Host Address
- CU Address: The unused address with same subnet DU and RIC
- RIC Address: RIC platfrom's Host Address

In the common case, O-DU connects CU_STUB and RIC_STUB with virtual interface. When O-DU integration with RIC, it will occur O-DU can't receive the reponse message from RIC. 
:::

``` shell=
cd src/cu_stub/
vim cu_stub.h
make clean_cu
```



**Compile the O-DU and CU Stub**

Compile the O-DU and CU Stub. It's not necessary to compile RIC Stub
```bash=
cd build/odu
make odu MACHINE=BIT64 MODE=FDD
make cu_stub NODE=TEST_STUB MACHINE=BIT64 MODE=FDD
```

Make Clean if needed:
```bash=
make clean_all
```

**Assign the virtual IP to network interface**
```bash=
sudo ifconfig eth1:CU_STUB "192.168.8.245"
```

## 4. Execution

### 4.1 Execute O-DU High
Open the 2 terminals to execute CU Stub and O-DU High
- CU_STUB
```bash=
cd l2/bin/cu_stub
./cu_stub
```

- DU
```bash=
cd l2/bin/odu
sudo ./odu
```


### 4.2 O-DU Prints RIC Indication Log

O-DU prints what measurement sends to KPM xApp in the terminal:

**RIC Indication which carries cell measurement**

![](https://hackmd.io/_uploads/rJlHpd4L2.png)


**RIC Indication which carries slice measurement**

![](https://hackmd.io/_uploads/Byt7a_4Ih.png)


### 4.3 Get the Measurement from InfluxDB

Enter the InfluxDB to check the stored measurements:
1. Show all running pods in the kubernetes.
```bash=
kubectl get pods -A
```
![](https://i.imgur.com/rcFIekv.png)

2. Enter InfluxDB containter
```bash=
# kubectl exec -it <influxDB's container ID> -n ricplt /bin/sh
kubectl exec -it ricplt-influxdb-meta-0 -n ricplt /bin/sh
```

3. Enter InfluxDB
```=
influx
```
![](https://i.imgur.com/MMUmHaY.png)

4. Login the InfluxDB
```=
auth
admin
UwuVmf6Tha
```
![](https://i.imgur.com/HEgfvUs.png)

> get password: `echo $(kubectl get secret ricplt-influxdb-auth -o "jsonpath={.data['influxdb-password']}" --namespace ricplt | base64 --decode)`

5. Print the databases of all namespace. The database named “kpm” is created.
```=
show databases
use kpm
```
![](https://i.imgur.com/M5X1VNp.png)

6. Print the created measurements
```=
show measurements
```
![](https://hackmd.io/_uploads/SJVz1FELn.png =300x)


7. List the all stored data
- Cell Measurement 
```=
select * from CellMetrics
```
![](https://hackmd.io/_uploads/H1EByKE8h.png)
![](https://hackmd.io/_uploads/rkO30OEUn.png)


- Slice Measurement 
```=
select * from SliceMetrics
```

![](https://hackmd.io/_uploads/BJkYxKNU2.png)
![](https://hackmd.io/_uploads/Bkg_eYNLh.png)

8. Insert the measurements by CLI
```=
INSERT <measurement name>,<tag1>=<value1> <tag2>=<value2>,<field1>=<value1> <field2>=<value2> <field3>=<value3>(, <timestmap>)

INSERT CellMetrics,RanName=testing DRB.UEThpDl=0i,RRU.PrbUsedDl=0i,RRU.PrbAvailDl=107i,RRU.PrbTotDl=0.0

INSERT SliceMetrics,RanName=testing,SliceID=01020304 DRB.UEThpDl.SNSSAI=0i,RRU.PrbUsedDl.SNSSAI=0i
```




## 5. Demo Video

{%youtube Ol6V-kIbyeU%}

## 6. Debug

### 6.1 Check if E2 Setup Response received successfully
In O-DU terminal, use Ctrl+F to search `E2setupresponse` if E2 Setup Response received. 

![](https://i.imgur.com/NnSqwWR.png =600x)


Sometime E2 Setup Failure may be received when O-DU tries to connect in the short period. If so, re-open the CU stub and O-DU again. 
![](https://i.imgur.com/v32VSRf.png =600x)

### 6.2 Check the registration in KPM xApp

Print the log to check if O-DU register in KPM xApp successfully.

1. Show all running pods in the kubernetes.
```bash=
kubectl get pods -A
```
![](https://i.imgur.com/rcFIekv.png)

2. Print the log of KPM xApp container.
```bash=
kubectl logs -n ricxapp -f ricxapp-kpm-6c9d89d46c-8lsc2
```
3. Check the registration log, and subscription response log
![](https://i.imgur.com/phqqGgP.png)


