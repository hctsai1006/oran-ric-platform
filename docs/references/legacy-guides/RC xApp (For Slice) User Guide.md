# RC xApp (For Slice) User Guide 
###### tags: `Thesis`

:::success
**Intro**:
In the G release, O-DU only finish the setup, subscription and indication message of E2AP. The control message doesn't finish so that O-DU can't be controlled by E2SM-RC.

Moreover, RC xApp only supports transmiting **Handover Control** to CU. BMW Lab. provides another version to transmit slice-level quote in the RAN Control Message to DU. 

Thus, it's the user guide to execute the modified O-DU and RC xApp to transmit RIC Control message. 

**Goal:**
- RC xApp configures the RRM Policy in O-DU Scheduler

Reference: 
- [Develop Record - Integrate [F] O-DU High & RC xApp](/hAuhFyUeQ8WiaoXk2WJ1Eg)
:::

[TOC]

## 1. Summary
RC xApp is deployed on RIC Platform and provides the basic implementation of  initiating spec compliant E2-SM RC based RIC Control Request message to the RAN/E2 Node. GRPC and RMR is used for communication.

GRPC interface support is introduced so other xApps can initiate GRPC based control Request to RC xapp, which in turn shall send the RIC Control Request to RAN/E2 Node.

However, the RC xApp only supports transmiting **Handover Control** to CU. BMW Lab. provides another version to transmit slice-level quote in the RAN Control Message to DU. 


### Environment
It's the environment in the testing. 

![](https://i.imgur.com/RQkaeEY.png)

**RIC Platform** 
- Repository: https://gerrit.o-ran-sc.org/r/ric-plt/ric-dep
- Version: F Release

**RC xApp**
- Repository: https://github.com/jackychiangtw/rc-xapp.git
- Version: Master, based on master (2/22)

**O-DU High**
- Repository: https://github.com/jackychiangtw/odu-bmwlab.git
- Version: Base on sch-slice-based (G Release)


### Payload
RIC Style and Control Action ID describes the features in this control message. For example, if **Control Style** is 2 for **Radio Resource Allocation Control** which defined in the E2SM-RC spec. Then look up the **Control Action ID** table of **Control Style** = 2. Slice-level PRB quota are found at **Control Action ID** = 6

![](https://i.imgur.com/ZkwEF5I.png =700x)


### Procedure

**E2AP**

It's the basic procedure of E2AP with RIC Control. After O-DU finished the E2 Setup procedure, Near-RT RIC can transmit the RIC Control Request to O-DU (E2 node). O-DU should process the E2SM-RC message of RIC Control Request message. 

![](https://i.imgur.com/yNMpIFj.png)

## 2. Installation

### 2.1 Install [F] RIC Platfrom

Follow this [user guide](https://hackmd.io/@Min-xiang/SJD9Xh5c9) to install RIC Platform.

### 2.2 Install (Slice feature) RC xApp 

**Compile the Images and Onboard the Container**

In the environment which installed RIC platform, follow the steps below to install RC xApp:

- Import charts url for `dms_cli`
```bash=
export NODE_PORT=$(kubectl get --namespace ricinfra -o jsonpath="{.spec.ports[0].nodePort}" services r4-chartmuseum-chartmuseum)
export NODE_IP=$(kubectl get nodes --namespace ricinfra -o jsonpath="{.items[0].status.addresses[0].address}")
export CHART_REPO_URL=http://$NODE_IP:$NODE_PORT/charts
```
- Onboard and install the RC xApp.
```=
cd rc
docker build -t nexus3.o-ran-sc.org:10002/o-ran-sc/ric-app-rc:1.0.4 .
cd xapp-descriptor/
dms_cli uninstall rc ricxapp
dms_cli onboard config.json schema.json 
dms_cli install rc 1.0.0 ricxapp
```
- Check if is installed successfully
```bash=
kubectl get pods -A
```
![](https://i.imgur.com/XePnS8V.jpg)

**The common commands to debug the error:**
- Print all container ID and its status
```bash=
kubectl get pods -A
```

> `-A` : Print container in all namespace

- Print the external port in container
```bash=
kubectl get svc -A
```

- Print the log from the container
```bash=
kubectl logs <container ID> -n <namespace> -f
```

> `-f` : Print the log in real time
> `-n` : Identify the namespace


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
vim <O-DU path>/src/du_app/du_cfg.h 
```

At line 33:

![](https://i.imgur.com/KsP4YCy.png)
:::info
- DU Address: O-DU's Host Address
- CU Address: The unused address with same subnet DU and RIC
- RIC Address: RIC platfrom's Host Address

In the common case, O-DU connects CU_STUB and RIC_STUB with virtual interface. When O-DU integration with RIC, it will occur O-DU can't receive the reponse message from RIC. 
:::


**Compile the O-DU and CU Stub**

Compile the O-DU and CU Stub. It's not necessary to compile RIC Stub
```bash=
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

## 3. Execution

### 3.1 Execute O-DU High
Open the 2 terminals to execute CU Stub and O-DU High
- CU_STUB
```bash=
cd <O-DU path>/bin/cu_stub
./cu_stub
```

- DU
```bash=
cd <O-DU path>/bin/odu
sudo ./odu
```

O-DU is ready for receiving RC message. 

### 3.2 Get the `ranName` from Routing Manager
RIC platform uses `ranName` parameter to identify E2 nodes. `ranName` consists of plmnID and gNB ID. `ranName` can be found in routing manager: 

Print Routing manager log:
```bash=
kubectl logs deployment-ricplt-e2term-alpha-78454fd4f5-85c9l -n ricplt
```
![](https://i.imgur.com/eQNyLcx.png)

The `ranName` is below the E2 setup Response. Keep it and it will be used in the next step. 

### 4.3 Determine Parameter of RRM Policy

Message format for RRM Policy:
- RRM Policy Group 1
    - Member 1:
        - PLMN ID: 6-bytes
        - SST: 1-bytes
        - SD: 3-bytes
    - Member 2:
        - PLMN ID: 6-bytes
        - SST: 1-bytes
        - SD: 3-bytes
    - Min PRB Ratio: 0~100 (Integer)
    - Max PRB Ratio: 0~100 (Integer)
    - Dedicated PRB Ratio: 0~100 (Integer)
- RRM Policy Group 2
    - Member 1:
        - PLMN ID: 6-bytes
        - SST: 1-bytes
        - SD: 3-bytes
    - Min PRB Ratio: 0~100 (Integer)
    - Max PRB Ratio: 0~100 (Integer)
    - Dedicated PRB Ratio: 0~100 (Integer)
- RRM Policy Group N...

RC xApp supports transmit any number of RRM Policy Group and its member. However O-DU only supports 1 member of each policy group at this moment.

Example:
- RRM Policy Group 1 (Slice 1)
    - Member 1:
        - PLMN ID: 311480
        - SST: {0x01}
        - SD: {0x02, 0x03, 0x04}
    - Min PRB Ratio: 25
    - Max PRB Ratio: 85
    - Dedicated PRB Ratio: 5
- RRM Policy Group 2 (Slice 2)
    - Member 1:
        - PlMN ID: 311480
        - SST: {0x02}
        - SD: {0x03, 0x03, 0x04}
    - Min PRB Ratio: 35
    - Max PRB Ratio: 75
    - Dedicated PRB Ratio: 15
- RRM Policy Group 3 (Slice 3)
    - Member 1:
        - PlMN ID: 311480
        - SST: {0x03}
        - SD: {0x04, 0x03, 0x04}
    - Min PRB Ratio: 35
    - Max PRB Ratio: 75
    - Dedicated PRB Ratio: 15

### 3.3 Modify grpcClient content
RC xApp has a GRPC server to receive a GRPC request containing RIC control request parameters from a GRPC client. It usually triggers from other xApp. 

In this note, we use scripts to send grpcClient to RC xApp. Modify `rc/unitTest/grpcClient.sh`

**1. Construct the data to json format with the parameters form previous step**
- Human-Readable
```json=
{
  "policy": [
    {
      "member": [
        {
          "plmnId": "311480",
          "sst": "01",
          "sd": "020304"
        }
      ],
      "minPRB": 25,
      "maxPRB": 85,
      "dedPRB": 5
    },
    {
      "member": [
        {
          "plmnId": "311480",
          "sst": "02",
          "sd": "030304"
        }
      ],
      "minPRB": 35,
      "maxPRB": 75,
      "dedPRB": 15
    },
    {
      "member": [
        {
          "plmnId": "311480",
          "sst": "03",
          "sd": "040304"
        }
      ],
      "minPRB": 35,
      "maxPRB": 80,
      "dedPRB": 25
    }
  ]
}
```

**2. Modify the script message in the file**: 
- Add the '\\' before every \" 
- Put the raw data above in the `rrmPolicy` field. 
- Modify `ranName` field as what you keeped at previous step.
- Fill in grpc server IP
```sh!
./grpcurl -plaintext -d "{\"ranName\": \"gnb_311_048_0000000a\", \"rrmPolicy\": [{\"member\": [{\"plmnId\" : \"311480\", \"sst\" : \"01\", \"sd\" : \"020304\"}] , \"minPRB\" : 25, \"maxPRB\" : 85, \"dedPRB\" : 5} , {\"member\": [{\"plmnId\" : \"311480\", \"sst\" : \"02\", \"sd\" : \"030304\"}], \"minPRB\" : 35, \"maxPRB\" : 75, \"dedPRB\" : 15}, {\"member\": [{\"plmnId\" : \"311480\", \"sst\" : \"03\", \"sd\" : \"040304\"}], \"minPRB\" : 35, \"maxPRB\" : 80, \"dedPRB\" : 25}]}" 10.110.245.140:7777 rc.MsgComm.SendRRMPolicyServiceGrpc
```
```json=

{
  "ranName": "gnb_311_048_0000000a",
  "rrmPolicy": [
    {
      "member": [
        {
          "plmnId": "311480",
          "sst": "01",
          "sd": "020304"
        }
      ],
      "minPRB": 25,
      "maxPRB": 85,
      "dedPRB": 5
    },
    {
      "member": [
        {
          "plmnId": "311480",
          "sst": "02",
          "sd": "030304"
        }
      ],
      "minPRB": 35,
      "maxPRB": 75,
      "dedPRB": 15
    },
    {
      "member": [
        {
          "plmnId": "311480",
          "sst": "03",
          "sd": "040304"
        }
      ],
      "minPRB": 35,
      "maxPRB": 80,
      "dedPRB": 25
    }
  ]
}
```
> In the script, "\\" is needed otherwise it is considered as the string.
 
> Get grpc server IP: `kubectl get svc -A`
![](https://hackmd.io/_uploads/SyMsCY482.png)


### 3.4 Trigger RC xApp to Send RIC Control
Execute `rc/unitTest/grpcClient.sh` to send the gRPC to RC xApp. It invokes RC xApp to send RIC Control Request with E2SM-RC encoded.

```bash=
./rc/unitTest/grpcClient.sh
```

RC xApp will response the successfully message. 

![](https://i.imgur.com/JyDTbOZ.png)

### 3.5 O-DU receives the RIC Control Message 

While RC xApp sends the RIC Control message, O-DU received RIC Control message from RC xApp. It deconstructs the RIC Control Message and the result is printed as below. 

The received parameters are shown in the screen:

![](https://hackmd.io/_uploads/HyWMnYN8n.png)


### 3.6 O-DU Reconfigures Slice Config in MAC Scheduler 

E2SM-RC Handler invokes the slice reconfiguration function in MAC and carries the slice-level quote parameters. The actual PRB quota will be calculated and reconfigured successfully per slice in the MAC Scheduler.

The reconfiguration logs are printed from DU App finally.

![](https://hackmd.io/_uploads/HyVmnK4In.png)


## 4. Demo Video
{%youtube uCfTtHM39Ms%}

## 5. Debug
### 5.1 Check if E2 Setup Response received successfully
In O-DU terminal, use Ctrl+F to search `E2setupresponse` if E2 Setup Response received. 

![](https://i.imgur.com/NnSqwWR.png =600x)


Sometime E2 Setup Failure may be received. If so, re-open the CU stub and O-DU again. 
![](https://i.imgur.com/v32VSRf.png =600x)

## 6. Push to OSC gerrit


Follow the [user guide](https://hackmd.io/@Yueh-Huan/HydYqyYH2#Step-1-Setup-SSH) from Yueh-Huan


![](https://hackmd.io/_uploads/B1NK3qzn3.png)

