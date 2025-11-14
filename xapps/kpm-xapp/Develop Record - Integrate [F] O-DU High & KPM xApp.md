# Develop Record - Integrate [F] O-DU High & KPM xApp
###### tags: `Thesis`

:::success
**Intro**:
In the G release, O-DU only finish the indication to RIC Stub. It doesn't support any service model and can't upload the actual data either. This note records the development step. 

**Goal**:
- [x] [Establish the connection of O-DU High and KPM xApp](https://hackmd.io/fSbe8RLdTWyage_Ev8r_xg#41-Establish-the-Connection-of-O-DU-High-and-KPM-xApp)
- [x] Integration of E2SM message
    - [x] [Integration of E2 Setup Request with O-DU High and KPM xApp](https://hackmd.io/fSbe8RLdTWyage_Ev8r_xg?view#421-Integration-of-E2-Setup-Request-with-O-DU-High-and-KPM-xApp)
    - [x] [Integration of RIC Subscription with O-DU High and KPM xApp](https://hackmd.io/fSbe8RLdTWyage_Ev8r_xg?view#422-Integration-of-RIC-Subscription-with-O-DU-High-and-KPM-xApp)
    - [x] [Integration of RIC Indication with O-DU High and KPM xApp](https://hackmd.io/fSbe8RLdTWyage_Ev8r_xg?view#423-Integration-of-RIC-Indication-with-O-DU-High-and-KPM-xApp)
- [x] [O-DU Reports Actual UE throughput](https://hackmd.io/fSbe8RLdTWyage_Ev8r_xg?view#43-O-DU-Reports-Actual-UE-throughput)
- [x] [KPM xApp stores the reported data in influxDB](https://hackmd.io/fSbe8RLdTWyage_Ev8r_xg?both#44-KPM-xApp-stores-the-reported-data-in-influxDB)
- [x] [Upgrade the KPM version to 2.03](https://hackmd.io/fSbe8RLdTWyage_Ev8r_xg?both#45-Upgrade-the-E2SM-KPM-version-to-203), 3/29
- [x] [Support Indication Message format 2](https://hackmd.io/fSbe8RLdTWyage_Ev8r_xg?both#46-Support-Indication-Message-Format-2), 3/30
- [x] [O-DU Reports Actual PRB Used For Traffic](https://hackmd.io/fSbe8RLdTWyage_Ev8r_xg?view#47-O-DU-Reports-Actual-PRB-Used-for-Traffic), 4/7
- [ ] Integration Demo:
    - O-DU reports the UE throughput to RIC
    - InfluxDB stores the measurements and able to be read

**Reference**
- [E2 Setup Request of E2SM-KPM v2.0](/zPRpGMUzSkOey72Wz9DOKg)
- [Subscription Request & Response of E2SM-KPM v2.0](/JdjR3IRATKOD9KxubRcUjw)
- [RIC Indication of E2SM-KPM v2.0](/CfABVrS0S8aI50GfezYqpg)
- [RC xApp (For Slice) User Guide](/TLj3c6ATTFiz4oESlftk3w)
- [Develop Record - Integrate [F] O-DU High & RC xApp](/hAuhFyUeQ8WiaoXk2WJ1Eg)
- [Slice xApp SLA Integration Demo](/ZQJsgQsXT12eYsxRZ65bQw)
:::

[TOC]

## 1. Summary
The KPM (Key Performance Management) xApp of O-RAN is a software application designed to provide real-time monitoring and analysis of network performance in a 5G O-RAN (Open Radio Access Network) environment.

This KPM xApp primarily provide the measurment for Slice xApp to configure the slice level, thus this xApp should support the measurement item which Slice xApp needs. 

### Environment
![](https://i.imgur.com/3KFTVHr.png)

**RIC Platform** 
- Repository: https://gerrit.o-ran-sc.org/r/ric-plt/ric-dep
- Version: F Release

**KPM xApp**
- Repository: Made by YuehHuan, N/A
- Version: 

**O-DU High**
- Repository: https://github.com/jackychiangtw/odu-e2rc.git -b sch_slice_based
- Version: Base on sch-slice-based (G Release)
- Date: 3/20

### Payload
- E2 Setup Request
E2AP defines the procedure and the basic data format. E2SM-KPM defines the the avaliable measurements from E2 node (O-DU). E2SM-KPM message is obtained in RAN function definition of E2AP.
    - E2 Setup Request (O-DU -> RIC)
![](https://i.imgur.com/l2z1fJz.png =300x)
    - E2 Setup Response (RIC -> O-DU): E2AP only

- RIC Subscription
E2SM-KPM defines the the subscribed measurements from xApp (Near-RT RIC).
    - RIC Subscription Request (RIC -> O-DU)
    ![](https://i.imgur.com/kKL4mvB.png =300x)
    - RIC Subscription Response (O-DU -> RIC)
    ![](https://i.imgur.com/Tyh5ya4.png =300x)

- RIC Indication
E2SM-KPM defines report measurement datas which xApp (Near-RT RIC) is subscribed.
![](https://i.imgur.com/sw0XESL.png =300x)

### MSC
It's the MSC to show procedure to be developed and show in the demo:

- Black line represents unchanged function
- Red line represents new function
- Brown line represents modified function

![](https://i.imgur.com/8wHTScv.png)

:::spoiler MSC
```
title KPM xApp Procedure

entryspacing 0.7
participantgroup #lightgreen **Near-RT RIC**
participant "InfluxDB" as DB
participant "KPM xApp" as xApp
participant "Subscription Manager" as submgr
participant "E2 Manager" as E2mgr
participant "E2 Termination" as E2
end

participantgroup #Aqua **O-DU High**
participant "DU App" as APP
participant "E2AP handler" as E2AP
participant "E2SM-KPM Module" as KPM
participant RLC
participant MAC
end

note over APP,MAC: Cell up
APP->E2AP: BuildAndSendE2SetupReq()
E2AP-#red>KPM: <color:#red>kpmBuildE2SetupReq()</color>
KPM-#red>E2AP: <color:#red>RAN Function Definition IE</color>
E2AP->APP: SendE2APMsg()
APP->E2: E2SetupRequest
E2mgr<-E2:E2SetupRequest
E2mgr->E2:E2SetupResponse
E2->APP: E2SetupResponse
APP->E2AP:E2APMsgHdlr()
box over E2AP: <color:#red>procE2SetupRsp()</color>

note over DB, MAC: Successfully Setup
xApp->submgr:REST Subscription Request
submgr->E2:RIC Subscription Request
E2->APP:RIC Subscription Request
APP->E2AP: E2APMsgHdlr()
box over E2AP: procRicSubsReq()
E2AP->#redKPM: <color:#red>kpmProcRicSubsReq()</color>
E2AP-#red>KPM:<color:#red>kpmProcRicSubsReq()</color>
KPM-#red>RLC: <color:#red>rlcStartTmr()</color>
RLC-#red>KPM: <color:#red>ROK</color>
KPM-#red>MAC: <color:#red>macStartTmr()</color>
MAC-#red>KPM: <color:#red>ROK</color>
KPM-#red>E2AP: <color:#red>ROK</color>
box over E2AP: BuildAndSendRicSubscriptionRsp()
E2AP->APP: SendE2APMsg()
E2<-APP:RIC Subscription Response

submgr<-E2:RIC Subscription Response
xApp<-submgr:REST Subscription Response
note over DB, MAC: Successfully Subscribed
loop Measurement Period (500ms)
box over RLC: <color:#brown>rlcTmrExpiry()</color>
RLC-#red>KPM: <color:#brown>UE Throguhput</color>
box over KPM: <color:#red>Store UE Throughput</color>
end
loop Measurement Period (50ms)
box over MAC: <color:#red>macTmrExpiry()</color>
MAC-#red>KPM: <color:#red>PRB Usage</color>
box over KPM: <color:#red>Store PRB Usage</color>
end
loop Reporting Period (500ms)
box over RLC: <color:#brown>rlcTmrExpiry()</color>
E2AP<#red-RLC: <color:#red>BuildAndSendRicIndication()</color>
E2AP-#red>KPM: <color:#red>kpmBuildRicIndication()</color>
box over KPM: <color:#red>Get L2 Metrics</color>
E2AP<#red-KPM: <color:#red>Indication Header,\nIndication Message IE</color>
E2AP<-KPM
E2AP->APP:SendE2APMsg()
end 
APP->E2:RIC Indication
E2->xApp:RIC Indication
DB<#red-xApp: <color:#red>Store Data</color>
```
:::



## 2. Installation
Follow the steps below to finish the installation

### 2.1 Install RIC Platform

Follow this [user guide](https://hackmd.io/@Min-xiang/SJD9Xh5c9) to install RIC Platform.

### 2.2 Install KPM xApp

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
cd kpm
docker build . -t docker.io/mb8746/kpm:0.0.2
cd config/
dms_cli uninstall kpm ricxapp
dms_cli onboard config-file.json schema.json 
dms_cli install kpm 0.0.2 ricxapp
```
- Check if is installed successfully
```bash=
kubectl get pods -A
```
![](https://i.imgur.com/XePnS8V.jpg)

### 2.3 Compile O-DU
**Install the necessary libraries**
:::info
Update newest package.
```shell=
sudo apt-get update

## If you can't use `ifconfig`, run below command to install tools.
sudo apt-get install net-tools -y
```

Install necessary libraries to build & compile O-DU high.
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


**Compile the O-DU and CU Stub**

Compile the O-DU and CU Stub. It's not necessary to compile RIC Stub
```bash=
make odu MACHINE=BIT64 MODE=FDD
make cu_stub NODE=TEST_STUB MACHINE=BIT64 MODE=FDD
```

Make Clean:
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
cd l2/bin/cu_stub
./cu_stub
```

- DU
```bash=
cd l2/bin/odu
sudo ./odu
```

### 3.2 Print the KPM xApp Log

- Print all container ID and its status
```bash=
kubectl get pods -A
```

> `-A` : Print container in all namespace

- Print the log from the container
```bash=
kubectl logs <container ID> -n <namespace> -f
```

> `-f` : Print the log in real time
> `-n` : Identify the namespace
> `--v=0` : Print the debug message


## 4. Development Record

### 4.1 Establish the Connection of O-DU High and KPM xApp

O-DU High sends the E2 Setup Request to Near-RT RIC. Near-RT RIC routes the message to KPM xApp. KPM xApp receives the message and establish the connection to O-DU.

Use the command to print the log from the container
```bash=
kubectl logs <container ID> -n <namespace> -f
```

![](https://i.imgur.com/PWD4P6t.png)

KPM xApp decodes the RAN Function Definition included in E2 Setup Reqeust. Currently O-DU haven't supported KPM service model so that KPM xApp returns the error. 

![](https://i.imgur.com/30jTUNH.png)

### 4.2 Integration of E2SM message

In the previous development, O-DU high has already connected to RIC stub. In this step, KPM xApp and O-DU can encode and send the message. They also can receive and decode the message. 

Previous Development:
- [E2 Setup Request of E2SM-KPM v2.0](/zPRpGMUzSkOey72Wz9DOKg)
- [Subscription Request & Response of E2SM-KPM v2.0](/JdjR3IRATKOD9KxubRcUjw)
- [RIC Indication of E2SM-KPM v2.0](/CfABVrS0S8aI50GfezYqpg)

Change to modified code and start to integrate the E2SM message

### 4.2.1 Integration of E2 Setup Request with O-DU High and KPM xApp

After modify the code, [compile O-DU](https://hackmd.io/fSbe8RLdTWyage_Ev8r_xg?view#23-Compile-O-DU) and execute the O-DU and CU stub. (KPM xApp already executed)

KPM xApp receives the E2 Setup Request message and judge if OID is equivalent to expected. If so, add the gNB ID into its database. 

![](https://i.imgur.com/yYa5FLe.png)


:::danger
**Debug log (3/21)**

**Description**

KPM xApp can decodes the E2 Setup Request message and get the RAN Function Description, but it can't get the OID to pass the recognization in E2 Setup Reqeust procedure. 
- Decoded message of RAN Function Description from KPM xApp
![](https://i.imgur.com/pUY6EgI.png)
- KPM xApp can't identify the OID in the RAN Function Description
![](https://i.imgur.com/V8ryYSO.png)


**Solution**

The ending character isn't equivalent. The ending character should be removed. 
Above is expected result and lower one is actual result.
![](https://i.imgur.com/aQ4MDww.png)

:::



### 4.2.2 Integration of RIC Subscription with O-DU High and KPM xApp

After KPM xApp receives the E2 Setup Request and gNB ID is added into KPM's database, KPM xApp sends RIC Subscription Request to O-DU High.

According to [payload](https://hackmd.io/fSbe8RLdTWyage_Ev8r_xg?view#Payload) defined in spec:
- Event Trigger Definition: It defines the reporting period of indication
- Action Definition: It defines datas which are subscribed.

There are 2 options to fill Action Definition item of RIC Subscription Request:
- Fixed data which supported by RIC Test
- Dynamic data which it's sent in E2 Setup Request

This note takes above one as example.

**Event Trigger Definition**
The message is decoded and get the Report period. 

![](https://i.imgur.com/FmRmjjH.png)

**Action Definition**
Measurement name is from Report Style List obtained in E2 Setup Request.
- Report Style in E2 Setup Request
![](https://i.imgur.com/MLaWQr7.png)
- Action Definition in RIC Subscription Request
![](https://i.imgur.com/kf3zQay.png)

The each field including Measurement name is able to get:
![](https://i.imgur.com/k66JOAN.png)

:::danger
**Debug Log (3/22)**

**Desciption**

O-DU can't decode the message. It returns the error 1, which represents `RC_WMORE,	/* More data expected, call again */`.

![](https://i.imgur.com/kMMWDFF.png =400x)

The decoded result is:
![](https://i.imgur.com/m8Idpvg.png)

I tried to decode in [unit test](https://hackmd.io/hAuhFyUeQ8WiaoXk2WJ1Eg#451-Create-the-unit-test-environment-for-testing) which running in C, but it's still failed and meet the same problem.

The original data is encoded in Action Definition Format 1. It is decoded successfully in unit test which running in golang. 
```c!
    char actionDefinFormat[] = {0, 1, 1, 8, 0, 22, 0, 160, 68, 82, 66, 46, 85, 69, 84, 104, 112, 68, 108, 1, 32, 0, 0, 0, 160, 68, 82, 66, 46, 85, 69, 84, 104, 112, 85, 108, 1, 32, 0, 0, 0, 176, 80, 69, 69, 46, 65, 118, 103, 80, 111, 119, 101, 114, 1, 32, 0, 0, 0, 144, 80, 69, 69, 46, 69, 110, 101, 114, 103, 121, 1, 32, 0, 0, 1, 144, 81, 111, 115, 70, 108, 111, 119, 46, 84, 111, 116, 80, 100, 99, 112, 80, 100, 117, 86, 111, 108, 117, 109, 101, 68, 108, 1, 32, 0, 0, 1, 144, 81, 111, 115, 70, 108, 111, 119, 46, 84, 111, 116, 80, 100, 99, 112, 80, 100, 117, 86, 111, 108, 117, 109, 101, 85, 108, 1, 32, 0, 0, 0, 160, 82, 82, 67, 46, 67, 111, 110, 110, 77, 97, 120, 1, 32, 0, 0, 0, 176, 82, 82, 67, 46, 67, 111, 110, 110, 77, 101, 97, 110, 1, 32, 0, 0, 0, 208, 82, 82, 85, 46, 80, 114, 98, 65, 118, 97, 105, 108, 68, 108, 1, 32, 0, 0, 0, 208, 82, 82, 85, 46, 80, 114, 98, 65, 118, 97, 105, 108, 85, 108, 1, 32, 0, 0, 0, 176, 82, 82, 85, 46, 80, 114, 98, 84, 111, 116, 68, 108, 1, 32, 0, 0, 0, 176, 82, 82, 85, 46, 80, 114, 98, 84, 111, 116, 85, 108, 1, 32, 0, 0, 0, 192, 82, 82, 85, 46, 80, 114, 98, 85, 115, 101, 100, 68, 108, 1, 32, 0, 0, 0, 192, 82, 82, 85, 46, 80, 114, 98, 85, 115, 101, 100, 85, 108, 1, 32, 0, 0, 0, 160, 86, 105, 97, 118, 105, 46, 71, 101, 111, 46, 120, 1, 32, 0, 0, 0, 160, 86, 105, 97, 118, 105, 46, 71, 101, 111, 46, 121, 1, 32, 0, 0, 0, 160, 86, 105, 97, 118, 105, 46, 71, 101, 111, 46, 122, 1, 32, 0, 0, 0, 192, 86, 105, 97, 118, 105, 46, 71, 110, 98, 68, 117, 73, 100, 1, 32, 0, 0, 0, 160, 86, 105, 97, 118, 105, 46, 78, 114, 67, 103, 105, 1, 32, 0, 0, 0, 160, 86, 105, 97, 118, 105, 46, 78, 114, 80, 99, 105, 1, 32, 0, 0, 1, 96, 86, 105, 97, 118, 105, 46, 82, 97, 100, 105, 111, 46, 97, 110, 116, 101, 110, 110, 97, 84, 121, 112, 101, 1, 32, 0, 0, 1, 32, 86, 105, 97, 118, 105, 46, 82, 97, 100, 105, 111, 46, 97, 122, 105, 109, 117, 116, 104, 1, 32, 0, 0, 1, 0, 86, 105, 97, 118, 105, 46, 82, 97, 100, 105, 111, 46, 112, 111, 119, 101, 114, 1, 32, 0, 0, 0, 0, 0, 0, 31, 1, 18, 52, 86, 0, 16};
```

**Solution**
The data type is `E2SM_KPM_ActionDefinition_t` instead of `E2SM_KPM_ActionDefinition_Format1_t`. Modify the correct type and success to get the measurement name from message. 

![](https://i.imgur.com/7ydFl8a.png)

:::

:::danger
**Debug Log (3/23)**

When KPM xApp uses dynamic data which it's sent in E2 Setup Request fill in Action Definition, it can't encode and send successfully. 

![](https://i.imgur.com/KZHJUig.png)

**Solution**
The error is at measurement info list. The type of cgo and C are different:

- In the header file of ASN.1 codec, it declare as `long` at `noLabel` field
![](https://i.imgur.com/BK2i4Dw.png)
- In the implementation in cgo, in declare as `int`
![](https://i.imgur.com/mWl6MsR.png)

:::


### 4.2.3 Integration of RIC Indication with O-DU High and KPM xApp

O-DU sends the RIC indication to KPM xApp. It carries to E2SM-KPM message: Indication Header and Indication Message. 

- Raw data in KPM xApp
![](https://i.imgur.com/cjKRx05.png)

- Decoded data in KPM xApp
![](https://i.imgur.com/3DsMEF3.png)
![](https://i.imgur.com/qVnsE6B.png)

- Indicaiton Header: It carries the starting time of collection (Timestamp of system time)
```xml=
<E2SM-KPM-IndicationHeader>
    <indicationHeader-formats>
        <indicationHeader-Format1>
            <colletStartTime>12 0C 1F 08</colletStartTime>
        </indicationHeader-Format1>
    </indicationHeader-formats>
</E2SM-KPM-IndicationHeader>
```

- Indication Message: It carries the measurement data and info. In this case, it carries the dummy data which represents downlink throughput. 
```xml=
<E2SM-KPM-IndicationMessage>
    <indicationMessage-formats>
        <indicationMessage-Format1>
            <measData>
                <MeasurementDataItem>
                    <measRecord>
                            <integer>2</integer>
                        
                    </measRecord>
                </MeasurementDataItem>
            </measData>
            <measInfoList>
                <MeasurementInfoItem>
                    <measType>
                        <measName>DRB.UEThpDl</measName>
                    </measType>
                    <labelInfoList>
                        <LabelInfoItem>
                            <measLabel>
                                <noLabel><true/></noLabel>
                            </measLabel>
                        </LabelInfoItem>
                    </labelInfoList>
                </MeasurementInfoItem>
            </measInfoList>
        </indicationMessage-Format1>
    </indicationMessage-formats>
</E2SM-KPM-IndicationMessage>
```

### 4.3 O-DU Reports Actual UE throughput

E2SM-KPM Manager locates in DU APP. It runs different thread to RLC, MAC, SCH which are L2 components. Basicly different threads can't share the same memory. To deal with this problem, O-DU uses TAPA task to call the function or exchange the data. 

![](https://i.imgur.com/tp3M3Pw.png)

In DU App, `duActvTsk()` function handles the input task from other components. Event `EVENT_RLC_SLICE_PM_TO_DU` invokes `DuProcRlcSliceMetrics()` to send the metrics which is UE's downlink throughput. Originally this is for O1 interface to report measurement. This can be modified to be used in E2 Interface. 

RLC calculate the throughput measurement and send to DU App. 

![](https://i.imgur.com/I68ddaO.png =500x)

DU App invokes the `BuildAndSendIndication()` to construct the indication message. The data are filled at Measurement Record field. 
![](https://i.imgur.com/IdOlqqL.png =500x)

KPM xApp is able to decode and get the DRB Downlink Throguhput:

![](https://i.imgur.com/K2Mtic0.png =700x)



> `ODU_SNSSAI_THROUGHPUT_PRINT_TIME_INTERVAL` parameter defines the interval of reporting the throguhput. (in milliseconds) Modify it to 3000ms.

:::danger
**Debug Log (3/24)**

**Problem 1**

After KPM xApp receives a RIC Indication Message from O-DU, it prints out the E2-timeout message. This message generally occurs at KPM xApp doesn't receive the RIC Subscription Message after E2 Setup. And this leads to KPM xApp stop receiving the indication message.

![](https://i.imgur.com/phAPhld.jpg)

**Solution (3/27)**

The mechanism of Subscription Manager is. Once RIC sent any RIC Subscription Request, E2 Node (O-DU) should response it in 2s. Or it will timeout and notify xApp. Meanwhile Routing Manager will delete the routing table of E2 node.

- Print the Subscription Manager in RIC Platform. 
![](https://i.imgur.com/C33mKYC.png)

However, Subscription Manager received the invaild subscription response. The RIC Requestor ID and RIC Instance ID of Request isn't equivalent to Response.

- Invaild subscription response
![](https://i.imgur.com/nuYqj6P.jpg)

Thus, modified the filling RIC Subscription Response in O-DU and RIC start to receive the RIC Indication Message continously.

<!-- **Problem 2**

After modfied the fields of RIC Subscription Response to correct. **Sometimes**, KPM xApp can't identify the notification from subscription manager and start to recieve RIC Indication.  -->

:::

### 4.4 KPM xApp stores the reported data in influxDB

KPM xApp receives the reported data and stores it in influxDB to be accessed by other xApp. 

This functionality is [demonstrated](https://wiki.o-ran-sc.org/download/attachments/3604609/KPIMON%20Demo%20Video.mp4?api=v2) by HCL: RIC Test which is E2 node simulator can report the data to KPIMON-GO xApp. KPIMON-GO assemble the metrics and store in database. This KPM xApp will re-use these functions and store the metrics from O-DU High. 

![](https://i.imgur.com/Gb4zqbu.png =600x)

After run the modified source code, KPM xApp started to store the data in influxDB. The steps of accessing the influxDB:

1. Enter the container of influxdb
```bash=
# kubectl exec -it <influxDB's container ID> -n ricplt /bin/sh
kubectl exec -it ricplt-influxdb-meta-0 -n ricplt /bin/sh
```
2. Enter the influxDB
```=
influx
```
3. Print the databases of all namespace. The database named "kpm" is created.
```=
show databases
use kpm
```
![](https://i.imgur.com/jjxx7Lk.png =500x)
4. Print the created measurements
```=
show measurements
```

![](https://i.imgur.com/1mrJZ3h.png =500x)
5. List the all stored data
```=
select * from ricIndication_cellMetrics
```
![](https://i.imgur.com/I2sijYX.png =500x)




:::danger
**Debug Log (3/27)**

Refer the source code by KPIMON-GO to report the metrics to database. Currently influxDB can't be accessed by KPM xApp. 

![](https://i.imgur.com/HJ1LE3K.png)

**Solution**

Find the solution by checking the data in the influxDB:

- Enter the container of influxdb
```bash=
kubectl exec -it ricplt-influxdb-meta-0 -n ricplt /bin/sh
```
- Login by username and password. [Get username/password](https://hackmd.io/@Min-xiang/SJD9Xh5c9#Issues-of-InfluxDB-amp-NFS)
```bash=
auth
```
- Show databases
```bash=
show databases
```
- Access the influx by service without authentication
```bash=
# curl -G 'http://<influxdb's service IP>:8086/query?pretty=true' --data-urlencode "db=mydb" --data-urlencode "q=SELECT \"value\" FROM \"cpu_load_short\" WHERE \"region\"='us-west'"
curl -G 'http://10.105.95.195:8086/query?pretty=true' --data-urlencode "db=mydb" --data-urlencode "q=SELECT \"value\" FROM \"cpu_load_short\" WHERE \"region\"='us-west'"
```
![](https://i.imgur.com/AhVFSct.png =600x)
- Access the influxDB by service without authentication
```bash=
# curl -G 'http://<influxdb's service IP>:8086/query?pretty=true&u=username&p=password' --data-urlencode "db=mydb" --data-urlencode "q=SELECT \"value\" FROM \"cpu_load_short\" WHERE \"region\"='us-west'"
curl -G 'http://10.105.95.195:8086/query?pretty=true&u=admin&p=UwuVmf6Tha' --data-urlencode "db=mydb" --data-urlencode "q=SELECT \"value\" FROM \"cpu_load_short\" WHERE \"region\"='us-west'"
```
![](https://i.imgur.com/L9QVQB1.png =500x)

The problem is authentication is failed, so that kpm xApp can't access the database.
:::


### 4.5 Upgrade the E2SM-KPM version to 2.03

At the E2SM-KPM version 2.03, E2SM-KPM adds functionality which supports the slice filter. O-DU (E2 node) can reports the measurement in the same slice. Thus it's necessary to upgrade.  

Generate the new codec by ASN1C. Follow this [step](https://hackmd.io/ToTtUyusT6e31BVfMdgB2A):

```bash=
asn1c <input files> -pdu=auto -fcompound-names -fno-include-deps -findirect-choice -gen-PER -gen-OER -no-gen-example
```
> Input files are ASN.1 definition in E2SM-KPM ver2.03 and E2SM ver2.0

Finish the follow step to replace the codec in KPM xApp and O-DU:

**KPM xApp**

1. Filter the generated file in `.c` and `.h` file. Put them in the `kpm/e2sm/lib` and `kpm/e2sm/header` corresponding.
2. Due to the declaration of `TestCondInfo_t` is changed, the paramters in Indication Message Type 2 should be modified as pointer. See the parameter `testCondInfo` in `e2sm.go` 

**O-DU**

Follow this [note](https://hackmd.io/ToTtUyusT6e31BVfMdgB2A) to change the E2SM-KPM codec in `src/codec_utils`




### 4.6 Support Indication Message Format 2

To fulfill the demend of slice xApp, O-DU should support the indication message format 2 to transmit the UE mertics within the same slice. (Indication Message formats transmit the mertic within the same cell) Meanwhile KPM xApp also needs to support decoding that format. 

O-DU sends the 2 report style items in the E2 Setup Request to represent O-DU supports Indication Message Format 1 and 2. 

![](https://i.imgur.com/rV8F5UI.png)

O-DU sends the Indication Message format 2. It means this mertics only within the UE which equals to this slice ID (S-NSSAI).

![](https://i.imgur.com/97BdMIQ.png)

KPM xApp shoulds decode that indication message, and store it into the influxDB with different measurements topic. Thus there are 2 types of measurements:
- Cell Mertic
- Slice Mertic

These 2 types of mertic can be found in InfluxDB.
![](https://i.imgur.com/nwNKm1s.png)

```bash=
kubectl exec -it ricplt-influxdb-meta-0 -n ricplt /bin/sh
influx
show databases
use kpm
show measurements
```

See the all data in the `ricIndication_sliceMetrics`

![](https://i.imgur.com/GmY1q0E.png)
```bash=
select * from ricIndication_sliceMetrics
```



:::danger
**Debug log (3/30)**

**Problem 1**
While O-DU sends the 2 Report style items in the E2 Setup Request, O-DU can't successfully receive the subscription message. The problem is related to free the memory. 

![](https://i.imgur.com/M3hVVYd.png)

**Solution 1**

When E2AP handler destruct the Subscription Response, it iterators the all items but only allocate the 1 memory.

**Problem 2**
Due to the definitions of S-NSSAI are different in RRC ASN.1 codec and E2 ASN.1 codec. The compiler uses the RRC's definition instead of E2's definition.

![](https://i.imgur.com/yXZqE7Q.png)

**Solution 2**

Modfify the include order in the compiler file. The argument of RRC should be behind to E2. 

![](https://i.imgur.com/JggzCjj.png)

:::


### 4.7 O-DU Reports Actual PRB Used for Traffic

Similar to [step 4.4](https://hackmd.io/fSbe8RLdTWyage_Ev8r_xg?view#44-KPM-xApp-stores-the-reported-data-in-influxDB), O-DU have to support report actual PRB used for traffic. Different to throughput, it is calculated in MAC instead of RLC. Beside that, MAC have neither existed function to report measurement to DU APP nor timer framework, so these 2 things are needed to develop in this step.

MAC provides the data below:
- Cell measurement: 
    - Mean DL PRB used for data traffic (RRU.PrbUsedDl)
    - DL total available PRB (RRU.PrbAvailDl)
    - DL Total PRB Usage (RRU.PrbTotDl)
- Slice mesaurement 
    - Mean DL PRB used for data traffic (RRU.PrbUsedDl.SNSSAI)

**Create MAC Event Timer** 

==This step is skipped, see the debug log==
<!-- 
After modified the source code, there are 3 timer to print the measurements:
- DL throughput Per UE
- DL throughput Per SNSSAI
- MAC PRB Used Per UE

![](https://i.imgur.com/BZLn5xB.png)


:::info
**Summary of O-DU Timer**


In O-DU, there are some common functions to execute timer functionality: 
- `cm5.x`
```c=
Void cmInitTimers ARGS((CmTimer* timers, uint8_t max));
Void cmPlcCbTq ARGS((CmTmrArg* arg));
Void cmRmvCbTq ARGS((CmTmrArg* arg));
Void cmPrcTmr ARGS((CmTqCp* tqCp, CmTqType* tq, PFV func));
Void cmRstCbTq ARGS((CmTmrArg* arg));
```

It is used in L2 components, such as RLC, MAC and SCH. MAC and SCH only created the functions but not used on any usage. 

RLC declares 9 events for timer. `EVENT_RLC_SNSSAI_THROUGHPUT_TMR` is event to calculate the throughput of slice. `EVENT_RLC_UE_THROUGHPUT_TMR` is for calculating the throughput of UE. (Cell)
- `rlc_utils.h`
```c=
#define EVENT_RLC_UMUL_REASSEMBLE_TMR     1
#define EVENT_RLC_AMUL_REASSEMBLE_TMR     2
#define EVENT_RLC_AMUL_STA_PROH_TMR       3
#define EVENT_RLC_AMDL_POLL_RETX_TMR      4
#define EVENT_RLC_WAIT_BNDCFM             5
#define EVENT_RLC_L2_TMR                  6
#define EVENT_RLC_UE_THROUGHPUT_TMR       7
#define EVENT_RLC_UE_DELETE_TMR           8
#define EVENT_RLC_SNSSAI_THROUGHPUT_TMR   9
```

There are 4 functions in RLC timer `rlc_timer.c`:
- `rlcStartTmr` : Start the timer. The parameter `Event` identifies the different event. 
- `rlcStopTmr` : Stop the timer. 
- `rlcTmrExpiry` : If timer is expired, this function will be called. The timer calls this function once in every `rlcStartTmr`. If wanted trigger continously, `rlcStartTmr` should be called again in this function. 
- `rlcBndTmrExpiry` : For binding Timer. 

The data structure of the timer are defined in `rlc_utils.h`. The throughput are stored in the same place. The variable `rlcCb` is the global parameter in RLC to hold information.

```c=
RlcCb *rlcCb[MAX_RLC_INSTANCES];   /*!< RLC global control block */
```

However, in the MAC it's declared in `mac.h`. The measurement information is lacked. 

```c=268
MacCb macCb;
```
:::
-->
<!--:::danger
**Debug Log (4/6)**

After modfied the code, the MAC timer can't find the event which I created in MAC. 

- Failed on checking the log in MAC
![](https://i.imgur.com/Zlsixpn.png)

- Successful example in RLC
![](https://i.imgur.com/zmLc4nA.png)

In the RLC, I only found it assigns the value `TMR_NONE` on `tmrEvnt`. It still finding whether assign the correct event ID on `tmrEvnt`
```c=168
  gCb->genCfg = *cfg;

   /* Timer Queue Control point initialization */
   rlcTqCp         = &(gCb->rlcTqCp);
   rlcTqCp->tmrLen = RLC_TMR_LEN;
   rlcTqCp->nxtEnt = 0;

   gCb->rlcThpt.inst = gCb->init.inst;
   gCb->rlcThpt.ueTputInfo.ueThptTmr.tmrEvnt = TMR_NONE;
   gCb->rlcThpt.ueTputInfo.numActvUe = 0;
   memset(gCb->rlcThpt.ueTputInfo.thptPerUe, 0, MAX_NUM_UE * sizeof(RlcThptPerUe));

   gCb->rlcThpt.snssaiTputInfo.snssaiThptTmr.tmrEvnt = TMR_NONE;
   
```

**Solution (4/7)**

Refers to [this note](https://hackmd.io/QRPD5ZvKTPShTZbBNw0myQ#GDB-Tools), debug with gdb tools. We found out the input paremeter isn't equivalent to parameter in the function. We checked the input and declration, input parameter should be a pointer. 

:::-->
<!-- :::danger
**Debug log (4/13)**

After creating the timer event in MAC and runnning the programming for a while, the MAC thread will be crashed. 

![](https://i.imgur.com/cs2xvKm.png)

![](https://i.imgur.com/i6s6nEr.png)

Before crashed, the invaild timer event occured:

![](https://i.imgur.com/cPxB7vS.png)

**Solution (4/19)**

To avoid interfere the timer in the MAC, we won't create the new timer event to trigger the reporting PRB event. We reports the measurement at `MacProcDlAlloc()` which it will invoked after Scheduler finishes the scheduling. 

Something is needed to beware, if the data want to transmit in TAPA task, use should allocate memory in function `MAC_ALLOC_SHRABL_BUF()`

::: -->


**Create TAPA Task Function Entry**

As mention in [step 4.3](https://hackmd.io/fSbe8RLdTWyage_Ev8r_xg?view#43-O-DU-Reports-Actual-UE-throughput), O-DU exchanges the data to different components which running in different thread by TAPA Task. RLC is able to send measurements but MAC. We will finish this functionality in this step.

DU APP receives the measurement from MAC successfully. However, the filling actual PRB data will be done by Dennis in the future. 

![](https://i.imgur.com/i4I0qiB.png)


1. Define the event for sending the performance metric
- `du_app_mac_inf.h`
```c=90
#define EVENT_MAC_PRB_METRIC_TO_DU   228
```
2. Define the data structure for TAPA task
- `du_app_mac_inf.h`
```c=1646
typedef struct macSlicePrbPmList
{
   uint8_t           usedPrb;
   uint8_t           totalPrb;
}MacSlicePrbPmList;

typedef struct macPrbPm
{
   uint8_t             sliceNum;
   MacSlicePrbPmList   **listOfMacPrbPm;
}MacPrbPm;
```
3. Define the TAPA task process function
- `mac_cfg_hdl.c`
```c=66
MacDuPrbPmFunc MacDuPrbPmOpts[] =
{
   packDuMacPrbPm,   /* packing for loosely coupled */
   DuProcMacPrbPm,   /* packing for tightly coupled */
   packDuMacPrbPm   /* packing for light weight loosly coupled */
};
```
- `du_app_mac_inf.h`
```c=1923
uint8_t DuProcMacPrbPm(Pst *pst, MacPrbPm *macPrbPm);
uint8_t packDuMacPrbPm(Pst *pst, MacPrbPm *macPrbPm);
uint8_t unpackDuMacPrbPm(MacDuPrbPmFunc func, Pst *pst, Buffer *mBuf);
```
4. Implement the sending function in MAC
- `mac_cfg_hdl.c`
```c=1062
uint8_t MacSendPrbPmToDu(MacPrbPm *macPrbPm)
{
    Pst  rspPst;
    
    memset(&rspPst, 0, sizeof(Pst));
    FILL_PST_MAC_TO_DUAPP(rspPst, EVENT_MAC_PRB_METRIC_TO_DU);
    return (*MacDuPrbPmOpts[rspPst.selector])(&rspPst, macPrbPm);

}```
5. Implement the receiving function in DU APP
- `du_msg_hdl.c`
```c=2038
uint8_t DuProcMacPrbPm(Pst *pst,  MacPrbPm *macPrbPm)
{
   if(macPrbPm)
   {
      DU_LOG("\nINFO  -->  DU_APP : MAC PRB Measurement received successfully ");
      DU_FREE_SHRABL_BUF(DU_APP_MEM_REGION, DU_POOL, macPrbPm, sizeof(MacPrbPm));
   }
   return ROK;
}
```
6. Implement LWLC method of pack/unpacking function
- `du_app_mac_inf.c`
```c=2245
/*******************************************************************
 *
 * @brief Pack and send PRB measurement from MAC to DU APP
 *
 * @details
 *
 *    Function : packDuMacPrbPm
 *
 *    Functionality:
 *       Pack and send PRB measurement from MAC to DU APP
 *
 * @params[in] 
 * @return ROK     - success
 *         RFAILED - failure
 *
 * ****************************************************************/
uint8_t packDuMacPrbPm(Pst *pst, MacPrbPm *macPrbPm)
{
   Buffer *mBuf = NULLP;

   if(pst->selector == ODU_SELECTOR_LWLC)
   {
      if (ODU_GET_MSG_BUF(pst->region, pst->pool, &mBuf) != ROK)
      {
         DU_LOG("\nERROR  --> MAC : Memory allocation failed at packDuMacPrbPm");
         return RFAILED;
      }
      /* pack the address of the structure */
      CMCHKPK(oduPackPointer,(PTR)macPrbPm, mBuf);
   }
   else
   {
      DU_LOG("\nERROR  -->  MAC: Only LWLC supported for packDuMacPrbPm");
      return RFAILED;
   }

   return ODU_POST_TASK(pst,mBuf);
}

/*******************************************************************
 *
 * @brief Unpack PRB measurement from MAC to DU APP
 *
 * @details
 *
 *    Function :unpackDuMacPrbPm 
 *
 *    Functionality: Unpack PRB measurement from MAC to DU APP
 *
 * @params[in] 
 * @return ROK     - success
 *         RFAILED - failure
 *
 * ****************************************************************/
uint8_t unpackDuMacPrbPm(MacDuPrbPmFunc func, Pst *pst, Buffer *mBuf)
{
   if(pst->selector == ODU_SELECTOR_LWLC)
   {
      MacPrbPm *macPrbPm = NULLP;

      /* unpack the address of the structure */
      CMCHKUNPK(oduUnpackPointer, (PTR *)&macPrbPm, mBuf);
      ODU_PUT_MSG_BUF(mBuf);
      return (*func)(pst, macPrbPm);
   }

   ODU_PUT_MSG_BUF(mBuf);
   return RFAILED;
}
```
7. Create the event in message router
- `du_mgr_msg_router.c`
```c=573
case EVENT_MAC_PRB_METRIC_TO_DU:
  {
     ret = unpackDuMacUeResetRsp(DuProcMacPrbPm, pst, mBuf);
     break;
  }
```

**Fill in the actual PRB measurement in data structure**

==To be finished after Dennis finish the milestone of slice-based scheduler (4/7)==


### 4.8 O-DU Reports UE Throughput per Cell

Beside slice measurement, O-DU reports cell measurement at the same time. They use different timer event so that should allocate different function to trigger. 

1. Define the event for sending the performance metric
- `du_app_rlc_inf.h`
```c=37
#define EVENT_RLC_UE_PM_TO_DU 223
```
2. Define the data structure for TAPA task
- `du_app_rlc_inf.h`
```c=303
/*Cell Metric for NW Slicing from RLC to DUAPP*/
typedef struct cellPm
{
  double ThpDl;
}CellPm;

typedef struct cellPmList
{
   uint8_t numUe;
   CellPm *ueRecord;
}CellPmList;
```
3. Define the TAPA task process function
- `rlc_upr_inf_api.c`
```c=66
RlcCellPmToDuFunc rlcCellPmOpts[] =
{
   packRlcDuCellPm,          /* 0 - loosely coupled */
   DuProcRlcCellMetrics,     /* 1 - tightly coupled */
   packRlcDuCellPm           /* 2 - LWLC loosely coupled */
};
```
- `du_app_rlc_inf.h`
```c=420
uint8_t packRlcDuCellPm(Pst *pst, CellPmList *cellStats);
uint8_t unpackRlcCellPm(RlcCellPmToDuFunc func, Pst *pst, Buffer *mBuf);
uint8_t DuProcRlcCellMetrics(Pst *pst, CellPmList *cellStats);
```
4. Implement the sending function in MAC
- `rlc_upr_inf_api.c`
```c=198
/*******************************************************************
 *
 * @brief Sends Cell Performance Metrics to DU APP
 *
 * @details
 *
 *    Function : rlcSendCellPmToDu 
 *
 *    Functionality:  Sends Performace Metrics per slice together to DU APP
 *
 * @params[in] Pst *pst, CellPmList *cellStats 
 *             
 * @return ROK     - success
 *         RFAILED - failure
 *
 * ****************************************************************/
uint8_t rlcSendCellPmToDu(Pst *pst, CellPmList *cellStats)
{
    return (*rlcCellPmOpts[pst->selector])(pst, cellStats);
}
```
- `rlc_upr_inf_api.h`
```c=25
uint8_t rlcSendCellPmToDu(Pst *pst, CellPmList *cellStats);

```
5. Implement the receiving function in DU APP
- `du_msg_hdl.c`
```c=2071
/*******************************************************************
*
* @brief Handles received Cell Metrics from RLC and forward it to O1 
*
* @details
*
*    Function : DuProcRlcCellMetrics
*
*    Functionality:
*      Handles received Cell Metrics from RLC and forward it to O1
*
* @params[in] Post structure pointer
*              CellPmList *celleStats
*
* @return ROK     - success
*         RFAILED - failure
*
* ****************************************************************/
uint8_t DuProcRlcCellMetrics(Pst *pst, CellPmList *cellStats)
{
    uint8_t sliceRecord = 0;

    DU_LOG("\nDEBUG  -->  DU APP : Received Cell Metrics");
    if(cellStats == NULLP)
    {
       DU_LOG("\nERROR  -->  DU APP : Empty Metrics");
       return RFAILED;
    }
    
   DU_FREE_SHRABL_BUF(pst->region, pst->pool, cellStats->sliceRecord, (cellStats->numUe) * (sizeof(UePm)));
   DU_FREE_SHRABL_BUF(pst->region, pst->pool, cellStats, sizeof(CellPmList));

   return ROK;
}
```


6. Implement LWLC method of pack/unpacking function
- `du_app_rlc_inf.c`
```c=945

/*******************************************************************
*
* @brief Packs and Sends Cell PM from RLC to DUAPP
*
* @details
*
*    Function : packRlcDuCellPm
*
*    Functionality:
*       Packs and Sends Cell Performance Metrics from RLC to DUAPP
*
*
* @params[in] Post structure pointer
*             CellPmList *cellStats
*
* @return ROK     - success
*         RFAILED - failure
*
* ****************************************************************/

uint8_t packRlcDuCellPm(Pst *pst, CellPmList *cellStats)
{
   Buffer *mBuf = NULLP;

   if(pst->selector == ODU_SELECTOR_LWLC)
   {
      if (ODU_GET_MSG_BUF(pst->region, pst->pool, &mBuf) != ROK)
      {
         DU_LOG("\nERROR  --> RLC : Memory allocation failed at packRlcDuCellPm");
         return RFAILED;
      }
      /* pack the address of the structure */
      CMCHKPK(oduPackPointer,(PTR)cellStats, mBuf);
   }
   else
   {
      DU_LOG("\nERROR  -->  RLC: Only LWLC supported for packRlcDuCellPm");
      return RFAILED;
   }

   return ODU_POST_TASK(pst,mBuf);
}

/*******************************************************************
*
* @brief Unpacks Cell PM received from RLC
*
* @details
*
*    Function : unpackRlcCellPm
*
*    Functionality:
*         Unpacks Cell Performance Metrics received from RLC
*
* @params[in] Pointer to Handler
*             Post structure pointer
*             Message Buffer
* @return ROK     - success
*         RFAILED - failure
*
* ****************************************************************/

uint8_t unpackRlcCellPm(RlcCellPmToDuFunc func, Pst *pst, Buffer *mBuf)
{
    if(pst->selector == ODU_SELECTOR_LWLC)
    {
       CellPmList *cellStats = NULLP;
       /* unpack the address of the structure */
       CMCHKUNPK(oduUnpackPointer, (PTR *)&cellStats, mBuf);
       ODU_PUT_MSG_BUF(mBuf);
       return (*func)(pst, cellStats);
    }
    else
    {
       /* Nothing to do for other selectors */
       DU_LOG("\nERROR  -->  RLC: Only LWLC supported for Cell Metrics ");
       ODU_PUT_MSG_BUF(mBuf);
    }

    return RFAILED;
}

```
7. Create the event in message router
- `du_mgr_msg_router.c`
```c=473
case EVENT_RLC_UE_PM_TO_DU:
                  {
                     ret = unpackRlcCellPm(DuProcRlcCellMetrics, pst, mBuf);
                     break;
                  }
```
<!-- 
![](https://i.imgur.com/6kRYBTl.png)

![](https://i.imgur.com/Qrx2TgK.png)
 -->
 
 
### 4.9 KPM xApp Classify Reported Data
KPM xApp receives the data below, and KPM xApp needs to classify the reported data. 
- Cell measurement: The UE measurement per cell transmits in Indication Message Format 1. The measurements include:
    - Average DL UE throughput in gNB (DRB.UEThpDl)
    - Mean DL PRB used for data traffic (RRU.PrbUsedDl)
    - DL total available PRB (RRU.PrbAvailDl)
    - DL Total PRB Usage (RRU.PrbTotDl)
- Slice mesaurement The UE measurement per slice transmits in Indication Message Format 3. The measurements include: 
    - Average DL UE throughput in slice (DRB.UEThpDl.SNSSAI)
    - Mean DL PRB used for data traffic (RRU.PrbUsedDl.SNSSAI)

Take indication message format 1 as example, it's the actual indication captured by O-DU.
```xml=
<E2SM-KPM-IndicationMessage-Format1>
    <measData>
        <MeasurementDataItem>
            <measRecord>
                    <integer>25</integer>
                
            </measRecord>
        </MeasurementDataItem>
        <MeasurementDataItem>
            <measRecord>
                    <integer>0</integer>
                
            </measRecord>
        </MeasurementDataItem>
        <MeasurementDataItem>
            <measRecord>
                    <integer>106</integer>
                
            </measRecord>
        </MeasurementDataItem>
        <MeasurementDataItem>
            <measRecord>
                    <real>0</real>
                
            </measRecord>
        </MeasurementDataItem>
    </measData>
    <measInfoList>
        <MeasurementInfoItem>
            <measType>
                <measName>DRB.UEThpDl</measName>
            </measType>
            <labelInfoList>
                <LabelInfoItem>
                    <measLabel>
                        <noLabel><true/></noLabel>
                    </measLabel>
                </LabelInfoItem>
            </labelInfoList>
        </MeasurementInfoItem>
        <MeasurementInfoItem>
            <measType>
                <measName>RRU.PrbUsedDl</measName>
            </measType>
            <labelInfoList>
                <LabelInfoItem>
                    <measLabel>
                        <noLabel><true/></noLabel>
                    </measLabel>
                </LabelInfoItem>
            </labelInfoList>
        </MeasurementInfoItem>
        <MeasurementInfoItem>
            <measType>
                <measName>RRU.PrbAvailDl</measName>
            </measType>
            <labelInfoList>
                <LabelInfoItem>
                    <measLabel>
                        <noLabel><true/></noLabel>
                    </measLabel>
                </LabelInfoItem>
            </labelInfoList>
        </MeasurementInfoItem>
        <MeasurementInfoItem>
            <measType>
                <measName>RRU.PrbTotDl</measName>
            </measType>
            <labelInfoList>
                <LabelInfoItem>
                    <measLabel>
                        <noLabel><true/></noLabel>
                    </measLabel>
                </LabelInfoItem>
            </labelInfoList>
        </MeasurementInfoItem>
    </measInfoList>
</E2SM-KPM-IndicationMessage-Format1>
```

There are 4 Measurement Data Items and Measurement Info Items. One `measRecord` value is belonged to one `measType`. In this case:
- DRB.UEThpDl = 0
- RRU.PrbUsedDl
- RRU.PrbAvailDl = 106
- RRU.PrbTotDl = 0

At KPM xApp side, it should assemble the key and value from the RIC Indication message and store it in the influxDB. 

This part, we can make the most of `reflect` library to get the parameter name in the typedef struct:

```go=
func writeFieldValue(name string, value interface{}, structPtr interface{}) error {
	structValue := reflect.ValueOf(structPtr).Elem()
	structFieldType := structValue.Type()
	fmt.Println(structFieldType)

	// Loop over the fields of the struct and check if the name matches the one we want to set.
	for i := 0; i < structValue.NumField(); i++ {
		field := structValue.Field(i)
		if strings.EqualFold(structFieldType.Field(i).Name, name) {
			// The name matches, so set the value of the field using reflection.
			if !field.CanSet() {
				return fmt.Errorf("cannot set value of field %q", name)
			}
			a, ok := value.(int)
			if ok{
				field.Set(reflect.ValueOf(a))
			}
			return nil
		}
	}

	// The field was not found in the struct.
	return fmt.Errorf("field %q not found in struct", name)
}
```

### 4.10 Fix some problems in KPM xApp

1. The format convertion from int to uint64 (4/21)
```go=
switch v := value.(type) {
    case int:
        field.SetInt(int64(v))
    case uint64:
        field.SetInt(int64(v))
    default:
        return fmt.Errorf("unsupported type %T for field %q", value, name)
}
```
2. Adjust the key and value in the influxDB (4/21)
    - Before
![](https://i.imgur.com/PfLVSlY.png)
    - After
![](https://i.imgur.com/KX9Jy2f.png)
```go=
p := influxdb2.NewPointWithMeasurement("SliceMetrics").
AddField("RanName", sliceMetrics.RanName).
AddField("SliceID", sliceMetrics.SliceID).
AddField("DRB.UEThpDl.SNSSAI", sliceMetrics.DRB_UEThpDl).
AddField("RRU.PrbUsedDl.SNSSAI", sliceMetrics.RRU_PrbUsedDl).
SetTime(time.Now())
```
3. The large number can't store in array (4/24)
-> Use `*C.long` to allocate the memory
```
var cast_integer *C.long = (*C.long)(unsafe.Pointer(&MeasurementRecordItem_C.choice[0]))
					measRecordItem = uint64(*cast_integer)
					xapp.Logger.Debug("Indication Message integer = %v", measRecordItem)
```
4. Remove the measurements in the Influxdb (4/21)
-> Command in InfluxDB:
```
DROP MEASUREMENT <measurement name>
```
5. Some memory of E2AP message can't be free, and the programming will crash  (4/21)
![](https://i.imgur.com/cReL6ux.png)
-> Skip freeing `CallProcessID`
6. Lack of 1 "RICaction-ToBeSetup-Item" in RIC Subscription Request. (Only send cell measurement subscription) (4/24)
-> Fixed
![](https://i.imgur.com/ex7a6Y7.png)
7. O-DU can't decode the Style 3 (Slice Measurements Subscription) (4/24)
-> Added in O-DU
8. O-DU process E2 Setup failure (Ongoing)
9. O-DU should not send RIC indication before subscription success (4/25)
-> Added bool to enable the ric indication
10. O-DU only reconfigures 1 slice (Ongoing)
11. O-DU sends RIC Control Acknowledge (4/25)
-> Added
12. Lack of "OR" flag in RIC Subscription Request (Ongoing)


### 4.11 O-DU APP gets PRB allocation result from Scheduler

O-DU APP got the measurements from MAC in the [step 4.7](https://hackmd.io/fSbe8RLdTWyage_Ev8r_xg?view#47-O-DU-Reports-Actual-PRB-Used-for-Traffic). However, MAC only stores the total PRB. O-DU APP needs the used PRB of each slice to report. Used PRB is stored in Scheduler. We modify the data structure between MAC and SCH so that used PRB can be sent over SCH -> MAC -> DU APP. 

1. Modify the MAC-SCH interface to add `PrbMetric`
    - mac_sch_interface
```c=1185
typedef struct dlSchedInfo
{
   uint16_t     cellId;  /* Cell Id */
   SchSlotValue schSlotValue;

   /* Allocation for broadcast messages */
   bool isBroadcastPres;
   DlBrdcstAlloc brdcstAlloc;

   /* Allocation for RAR message */
   RarAlloc *rarAlloc[MAX_NUM_UE];

   /* UL grant in response to BSR */
   DciInfo    *ulGrant;

   /* Allocation from dedicated DL msg */
   DlMsgSchInfo *dlMsgAlloc[MAX_NUM_UE];

   /*Append by Jacky for E2 interface report per cell*/
   PrbMetric prbMetric;

}DlSchedInfo;
```
2. Fill in this PRB metric when SCH sends the slot report to MAC
    - `sch_slot_ind.c`
```c=747
   SchSliceBasedSliceCb *sliceCb = NULLP;
   SchSliceBasedCellCb  *schSpcCell = (SchSliceBasedCellCb *)cell->schSpcCell;
   CmLList *sliceCbNode = schSpcCell->sliceCbList.first;
   int slice_cnt = 0;
   dlSchedInfo.prbMetric.usedPrb = 0;

   dlSchedInfo.prbMetric.sliceNum = schSpcCell->sliceCbList.count;
   if(dlSchedInfo.prbMetric.listOfSlicePm == NULL && dlSchedInfo.prbMetric.sliceNum > 0){
      SCH_ALLOC(dlSchedInfo.prbMetric.listOfSlicePm, dlSchedInfo.prbMetric.sliceNum * sizeof(SchSlicePrbPmList*));
   }
      
   while(sliceCbNode)
   {
      sliceCb = (SchSliceBasedSliceCb *)sliceCbNode->node;
      if(slice_cnt < dlSchedInfo.prbMetric.sliceNum){
            if(dlSchedInfo.prbMetric.listOfSlicePm[slice_cnt] == NULL)
               SCH_ALLOC(dlSchedInfo.prbMetric.listOfSlicePm[slice_cnt], sizeof(SchSlicePrbPmList));
            dlSchedInfo.prbMetric.listOfSlicePm[slice_cnt]->usedPrb = sliceCb->allocatedPrb;
            dlSchedInfo.prbMetric.usedPrb += sliceCb->allocatedPrb;
            slice_cnt = slice_cnt + 1;
      }
      else{
         DU_LOG("\nJacky  -->  SCH SliceCB is oversize");
      }
      sliceCbNode = sliceCbNode->next;
   }

   
   ret = sendDlAllocToMac(&dlSchedInfo, schInst);
```
3. Fill in the data structure for MAC-DU APP interface which creates in [step 4.7](https://hackmd.io/fSbe8RLdTWyage_Ev8r_xg?view#47-O-DU-Reports-Actual-PRB-Used-for-Traffic)

### 4.12 O-DU Frees Dynamic Memory Allocation
MAC reports the PRB allocation every TTI, that is every 1ms. If the memory allocation doesn't be free, O-DU can't allocate new memory anymore. It may occur in DU APP, MAC or SCH. 

- Scheduler
![](https://hackmd.io/_uploads/S1gVzaOVh.png)

- DU APP (E2 Handler)
![](https://hackmd.io/_uploads/Bya4Mp_Nn.png)

To avoid that, every memory allocation should be free after used. However, there are some types of allocation in O-DU:

1. Default allocation: Allocate the memory by `calloc()`, `malloc()` which the method by gcc. This memory should be free by `free()`
2. OSC allocation:  Allocate the memory by `DU_ALLOC()`, `SCH_ALLOC` which the method by OSC. This memory should be free by `DU_FREE()`, `SCH_FREE()`

### 4.13 O-DU supports E2SM-KPM v2.02 and v3.00 simultaneously
Modify the O-DU asn.1 codec to let E2SM-KPM supports different versions at the same time. O-DU can distinguish the version by RAN Function ID or decode until successfully.

The merged ASN.1 definition:
:::spoiler ASN\. 1 Definition
```c=
-- ASN1START
-- **************************************************************
-- E2SM-KPM Information Element Definitions
-- **************************************************************

E2SM-KPM-IEs {
iso(1) identified-organization(3) dod(6) internet(1) private(4) enterprise(1) oran(53148) e2(1) version2(2) e2sm(2) e2sm-KPMMON-IEs (2)}

DEFINITIONS AUTOMATIC TAGS ::=

BEGIN

-- **************************************************************
--	IEs
-- **************************************************************

IMPORTS
    CGI,
    FiveQI,
    PLMNIdentity,
    QCI,
    QosFlowIdentifier,
    RANfunction-Name,
    RIC-Format-Type,
    RIC-Style-Name,
    RIC-Style-Type,
    S-NSSAI,
    UEID
FROM E2SM-COMMON-IEs;

TimeStamp ::= OCTET STRING (SIZE(4))

TimeStamp-v300 ::= OCTET STRING (SIZE(8))

BinIndex ::= INTEGER (1.. 65535, ...)

BinRangeValue ::= CHOICE {
	valueInt				INTEGER,
	valueReal			REAL,
	...
}

GranularityPeriod ::= INTEGER (1.. 4294967295)

LogicalOR ::= ENUMERATED {true, ...}


MeasurementType ::= CHOICE {
    measName	MeasurementTypeName,
    measID	    MeasurementTypeID,
    ...
}

MeasurementTypeName ::= PrintableString(SIZE(1.. 150, ...))

MeasurementTypeID ::= INTEGER (1.. 65536, ...)

MeasurementLabel ::= SEQUENCE {
    noLabel             ENUMERATED {true, ...}          OPTIONAL,
    plmnID              PLMNIdentity                    OPTIONAL,
    sliceID             S-NSSAI                         OPTIONAL,
    fiveQI	            FiveQI                          OPTIONAL,
    qFI	                QosFlowIdentifier	            OPTIONAL,
    qCI	                QCI	                            OPTIONAL,
    qCImax	            QCI	                            OPTIONAL,
    qCImin              QCI                             OPTIONAL,
    aRPmax              INTEGER (1.. 15, ...)           OPTIONAL,
    aRPmin              INTEGER (1.. 15, ...)           OPTIONAL,
    bitrateRange        INTEGER (1.. 65535, ...)        OPTIONAL,
    layerMU-MIMO        INTEGER (1.. 65535, ...)        OPTIONAL,
    sUM                 ENUMERATED {true, ...}          OPTIONAL,
    distBinX            INTEGER (1.. 65535, ...)        OPTIONAL,
    distBinY            INTEGER (1.. 65535, ...)        OPTIONAL,
    distBinZ            INTEGER (1.. 65535, ...)        OPTIONAL,
    preLabelOverride    ENUMERATED {true, ...}          OPTIONAL,
    startEndInd         ENUMERATED {start, end, ...}    OPTIONAL,
    min                 ENUMERATED {true, ...}          OPTIONAL,
    max                 ENUMERATED {true, ...}          OPTIONAL,
    avg                 ENUMERATED {true, ...}          OPTIONAL,
    ...
}

MeasurementLabel-v300 ::= SEQUENCE {
	noLabel					ENUMERATED {true, ...}				OPTIONAL,
	plmnID					PLMNIdentity							OPTIONAL,
	sliceID					S-NSSAI									OPTIONAL,
	fiveQI					FiveQI									OPTIONAL,
	qFI						QosFlowIdentifier						OPTIONAL,
	qCI						QCI										OPTIONAL,
	qCImax					QCI										OPTIONAL,
	qCImin					QCI										OPTIONAL,
	aRPmax					INTEGER (1.. 15, ...)				OPTIONAL,
	aRPmin					INTEGER (1.. 15, ...)				OPTIONAL,
	bitrateRange			INTEGER (1.. 65535, ...)			OPTIONAL,
	layerMU-MIMO			INTEGER (1.. 65535, ...)			OPTIONAL,
	sUM						ENUMERATED {true, ...}				OPTIONAL,
	distBinX					INTEGER (1.. 65535, ...)			OPTIONAL,
	distBinY					INTEGER (1.. 65535, ...)			OPTIONAL,
	distBinZ					INTEGER (1.. 65535, ...)			OPTIONAL,
	preLabelOverride		ENUMERATED {true, ...}				OPTIONAL,
	startEndInd				ENUMERATED {start, end, ...}		OPTIONAL,
	min						ENUMERATED {true, ...}				OPTIONAL,
	max						ENUMERATED {true, ...}				OPTIONAL,
	avg						ENUMERATED {true, ...}				OPTIONAL,
	...,
	ssbIndex					INTEGER (1.. 65535, ...)			OPTIONAL,
	nonGoB-BFmode-Index	INTEGER (1.. 65535, ...)			OPTIONAL,
	mIMO-mode-Index		INTEGER (1.. 2, ...)					OPTIONAL
}


TestCondInfo ::= SEQUENCE{
    testType    TestCond-Type,
    testExpr	TestCond-Expression	OPTIONAL,
    testValue   TestCond-Value	    OPTIONAL,
    ...	
}    

TestCond-Type ::= CHOICE{
    gBR 	ENUMERATED {true, ...},
    aMBR	ENUMERATED {true, ...},
    isStat	ENUMERATED {true, ...},
    isCatM	ENUMERATED {true, ...},
    rSRP	ENUMERATED {true, ...},
    rSRQ	ENUMERATED {true, ...},
    ...,
    ul-rSRP	ENUMERATED {true, ...},
    cQI	    ENUMERATED {true, ...},
    fiveQI	ENUMERATED {true, ...},
    qCI	    ENUMERATED {true, ...},
    sNSSAI	ENUMERATED {true, ...}
}

TestCond-Expression ::= ENUMERATED {
    equal,
    greaterthan,
    lessthan,
    contains,
    present,
    ...
}

TestCond-Value ::= CHOICE{
    valueInt	INTEGER,
    valueEnum	INTEGER,
    valueBool	BOOLEAN,
    valueBitS	BIT STRING,
    valueOctS	OCTET STRING,
    valuePrtS	PrintableString,
    ...,
    valueReal	REAL
}

-- **************************************************************
--	Lists
-- **************************************************************

maxnoofCells	            INTEGER ::= 16384
maxnoofRICStyles	        INTEGER ::= 63
maxnoofMeasurementInfo	    INTEGER ::= 65535
maxnoofLabelInfo	        INTEGER ::= 2147483647
maxnoofMeasurementRecord	INTEGER ::= 65535
maxnoofMeasurementValue	    INTEGER ::= 2147483647
maxnoofConditionInfo	    INTEGER ::= 32768
maxnoofUEID	                INTEGER ::= 65535
maxnoofConditionInfoPerSub  INTEGER ::= 32768
maxnoofUEIDPerSub	        INTEGER ::= 65535
maxnoofUEMeasReport	        INTEGER ::= 65535
maxnoofBin						INTEGER ::= 65535

BinRangeDefinition ::= SEQUENCE {
binRangeListX		BinRangeList, 
binRangeListY		BinRangeList			OPTIONAL -- This IE shall not be present for a distribution measurement type that doesn't use Distribution Bin Y --,
binRangeListZ		BinRangeList			OPTIONAL -- This IE shall not be present for a distribution measurement type that doesn't use Distribution Bin Z --,
...
}

BinRangeList ::= SEQUENCE (SIZE(1..maxnoofBin)) OF BinRangeItem

BinRangeItem ::= SEQUENCE {
	binIndex				BinIndex,
	startValue			BinRangeValue,
	endValue				BinRangeValue,
	...
}

DistMeasurementBinRangeList ::= SEQUENCE (SIZE(1..maxnoofMeasurementInfo)) OF DistMeasurementBinRangeItem

DistMeasurementBinRangeItem ::= SEQUENCE {
	measType				MeasurementType,
	binRangeDef			BinRangeDefinition,
	...
}

MeasurementInfoList ::= SEQUENCE (SIZE(1..maxnoofMeasurementInfo)) OF MeasurementInfoItem
MeasurementInfoItem ::= SEQUENCE {
    measType	    MeasurementType,
    labelInfoList	LabelInfoList,
    ...
}

LabelInfoList ::= SEQUENCE (SIZE(1..maxnoofLabelInfo)) OF LabelInfoItem

LabelInfoItem ::= SEQUENCE {
    measLabel	MeasurementLabel,
    ...
}

MeasurementInfoList-v300 ::= SEQUENCE (SIZE(1..maxnoofMeasurementInfo)) OF MeasurementInfoItem-v300

MeasurementInfoItem-v300 ::= SEQUENCE {
	measType				MeasurementType,
	labelInfoList		LabelInfoList-v300,
	...
}

LabelInfoList-v300 ::= SEQUENCE (SIZE(1..maxnoofLabelInfo)) OF LabelInfoItem-v300

LabelInfoItem-v300 ::= SEQUENCE {
	measLabel			MeasurementLabel-v300,
	...
}

MeasurementData ::= SEQUENCE (SIZE(1..maxnoofMeasurementRecord)) OF MeasurementDataItem

MeasurementDataItem ::= SEQUENCE {
    measRecord	    MeasurementRecord,
    incompleteFlag	ENUMERATED {true, ...}	OPTIONAL,
    ...
}

MeasurementRecord ::= SEQUENCE (SIZE(1..maxnoofMeasurementValue)) OF MeasurementRecordItem

MeasurementRecordItem ::= CHOICE {
    integer	INTEGER (0.. 4294967295),
    real	REAL,
    noValue	NULL,
    ...
}

MeasurementInfo-Action-List ::= SEQUENCE (SIZE(1..maxnoofMeasurementInfo)) OF MeasurementInfo-Action-Item

MeasurementInfo-Action-Item ::= SEQUENCE {
    measName	MeasurementTypeName,
    measID	    MeasurementTypeID	    OPTIONAL,
    ...
}

MeasurementCondList ::= SEQUENCE (SIZE(1..maxnoofMeasurementInfo)) OF MeasurementCondItem

MeasurementCondItem ::= SEQUENCE {
    measType	MeasurementType,
    matchingCond	MatchingCondList,
    ...
}

MeasurementCondUEidList ::= SEQUENCE (SIZE(1..maxnoofMeasurementInfo)) OF MeasurementCondUEidItem

MeasurementCondUEidItem ::= SEQUENCE {
    measType	        MeasurementType,
    matchingCond	    MatchingCondList,
    matchingUEidList	MatchingUEidList	OPTIONAL,
    ...
}

MatchingCondList ::= SEQUENCE (SIZE(1..maxnoofConditionInfo)) OF MatchingCondItem

MatchingCondItem ::= CHOICE{
    measLabel	    MeasurementLabel,
    testCondInfo	TestCondInfo,
    ...
}	

MeasurementInfo-Action-List-v300 ::= SEQUENCE (SIZE(1..maxnoofMeasurementInfo)) OF MeasurementInfo-Action-Item-v300

MeasurementInfo-Action-Item-v300 ::= SEQUENCE {
	measName				MeasurementTypeName,
	measID				MeasurementTypeID				OPTIONAL,
	...,
	binRangeDef			BinRangeDefinition			OPTIONAL
}

MeasurementCondList-v300 ::= SEQUENCE (SIZE(1..maxnoofMeasurementInfo)) OF MeasurementCondItem-v300

MeasurementCondItem-v300 ::= SEQUENCE {
	measType				MeasurementType,
	matchingCond		MatchingCondList-v300,
	...,
	binRangeDef			BinRangeDefinition			OPTIONAL
}

MeasurementCondUEidList-v300 ::= SEQUENCE (SIZE(1..maxnoofMeasurementInfo)) OF MeasurementCondUEidItem-v300

MeasurementCondUEidItem-v300 ::= SEQUENCE {
	measType					MeasurementType,
	matchingCond			MatchingCondList-v300,
	matchingUEidList		MatchingUEidList			OPTIONAL,
	...,
	matchingUEidPerGP		MatchingUEidPerGP			OPTIONAL
}

MatchingCondList-v300 ::= SEQUENCE (SIZE(1..maxnoofConditionInfo)) OF MatchingCondItem-v300

MatchingCondItem-v300 ::= SEQUENCE {
matchingCondChoice	MatchingCondItem-Choice,
logicalOR				LogicalOR						OPTIONAL,
...
}

MatchingCondItem-Choice ::= CHOICE{
	measLabel			MeasurementLabel-v300,
	testCondInfo		TestCondInfo,
	...
}


MatchingUEidList ::= SEQUENCE (SIZE(1..maxnoofUEID)) OF MatchingUEidItem

MatchingUEidItem ::= SEQUENCE{
    ueID	    UEID,
    ...
}

MatchingUEidPerGP ::= SEQUENCE (SIZE(1..maxnoofMeasurementRecord)) OF MatchingUEidPerGP-Item

MatchingUEidPerGP-Item ::= SEQUENCE{
	matchedPerGP				CHOICE{
		noUEmatched 				ENUMERATED {true, ...},
		oneOrMoreUEmatched		MatchingUEidList-PerGP,
		...
	},
	...
}

MatchingUEidList-PerGP ::= SEQUENCE (SIZE(1..maxnoofUEID)) OF MatchingUEidItem-PerGP

MatchingUEidItem-PerGP ::= SEQUENCE{
	ueID					UEID,
	...
}

MatchingUeCondPerSubList ::= SEQUENCE (SIZE(1..maxnoofConditionInfoPerSub)) OF MatchingUeCondPerSubItem

MatchingUeCondPerSubItem ::= SEQUENCE{
    testCondInfo	TestCondInfo,
    ...
}

MatchingUeCondPerSubList-v300 ::= SEQUENCE (SIZE(1..maxnoofConditionInfoPerSub)) OF MatchingUeCondPerSubItem-v300

MatchingUeCondPerSubItem-v300 ::= SEQUENCE{
	testCondInfo		TestCondInfo,
	...,
	logicalOR			LogicalOR				OPTIONAL
}

MatchingUEidPerSubList ::= SEQUENCE (SIZE(2..maxnoofUEIDPerSub)) OF MatchingUEidPerSubItem

MatchingUEidPerSubItem ::= SEQUENCE{
    ueID	    UEID,
    ...
}

UEMeasurementReportList ::= SEQUENCE (SIZE(1..maxnoofUEMeasReport)) OF UEMeasurementReportItem

UEMeasurementReportItem ::= SEQUENCE{
    ueID	    UEID,
    measReport	E2SM-KPM-IndicationMessage-Format1,
    ...
}

UEMeasurementReportList-v300 ::= SEQUENCE (SIZE(1..maxnoofUEMeasReport)) OF UEMeasurementReportItem-v300

UEMeasurementReportItem-v300 ::= SEQUENCE{
	ueID				UEID,
	measReport		E2SM-KPM-IndicationMessage-Format1-v300,
	...
}
	
-- **************************************************************
-- E2SM-KPM Service Model IEs
-- **************************************************************
	
-- **************************************************************
--	Event Trigger Definition OCTET STRING contents
-- **************************************************************
	
E2SM-KPM-EventTriggerDefinition ::= SEQUENCE{
    eventDefinition-formats	CHOICE{
        eventDefinition-Format1	E2SM-KPM-EventTriggerDefinition-Format1,
        ...
    },
    ...
}
	
E2SM-KPM-EventTriggerDefinition-Format1 ::= SEQUENCE{
    reportingPeriod	INTEGER (1.. 4294967295),
    ...
}
	
-- **************************************************************
--	Action Definition OCTET STRING contents
-- **************************************************************
	
E2SM-KPM-ActionDefinition ::= SEQUENCE{
    ric-Style-Type	            RIC-Style-Type,
    actionDefinition-formats	CHOICE{
        actionDefinition-Format1	E2SM-KPM-ActionDefinition-Format1,
        actionDefinition-Format2	E2SM-KPM-ActionDefinition-Format2,
        actionDefinition-Format3	E2SM-KPM-ActionDefinition-Format3,
        ...,
        actionDefinition-Format4	E2SM-KPM-ActionDefinition-Format4,
        actionDefinition-Format5	E2SM-KPM-ActionDefinition-Format5
    },
    ...
}
	
E2SM-KPM-ActionDefinition-Format1 ::= SEQUENCE {
    measInfoList	MeasurementInfoList,
    granulPeriod	GranularityPeriod,
    cellGlobalID	CGI	                OPTIONAL,
    ...
}
	
E2SM-KPM-ActionDefinition-Format2 ::= SEQUENCE {
    ueID	        UEID,
    subscriptInfo	E2SM-KPM-ActionDefinition-Format1,
    ...
}

E2SM-KPM-ActionDefinition-Format3 ::= SEQUENCE {
    measCondList	MeasurementCondList,
    granulPeriod	GranularityPeriod,
    cellGlobalID	CGI	                OPTIONAL,
    ...
}
	
E2SM-KPM-ActionDefinition-Format4 ::= SEQUENCE {
    matchingUeCondList	MatchingUeCondPerSubList,
    subscriptionInfo	E2SM-KPM-ActionDefinition-Format1,
    ...
}
	
E2SM-KPM-ActionDefinition-Format5 ::= SEQUENCE {
    matchingUEidList	MatchingUEidPerSubList,
    subscriptionInfo	E2SM-KPM-ActionDefinition-Format1,
    ...
}

E2SM-KPM-ActionDefinition-v300 ::= SEQUENCE{
	ric-Style-Type					RIC-Style-Type,
	actionDefinition-formats 	CHOICE{
		actionDefinition-Format1		E2SM-KPM-ActionDefinition-Format1-v300,
		actionDefinition-Format2		E2SM-KPM-ActionDefinition-Format2-v300,
		actionDefinition-Format3		E2SM-KPM-ActionDefinition-Format3-v300,
		...,
		actionDefinition-Format4		E2SM-KPM-ActionDefinition-Format4-v300,
		actionDefinition-Format5		E2SM-KPM-ActionDefinition-Format5-v300
	},
	...
}

E2SM-KPM-ActionDefinition-Format1-v300 ::= SEQUENCE {
	measInfoList					MeasurementInfoList-v300,
	granulPeriod					GranularityPeriod,
	cellGlobalID					CGI							OPTIONAL,
	...,
	distMeasBinRangeInfo			DistMeasurementBinRangeList		OPTIONAL
}

E2SM-KPM-ActionDefinition-Format2-v300 ::= SEQUENCE {
	ueID								UEID,
	subscriptInfo					E2SM-KPM-ActionDefinition-Format1-v300,
	...
}

E2SM-KPM-ActionDefinition-Format3-v300 ::= SEQUENCE {
	measCondList					MeasurementCondList-v300,
	granulPeriod					GranularityPeriod,
	cellGlobalID					CGI							OPTIONAL,
	...
}

E2SM-KPM-ActionDefinition-Format4-v300 ::= SEQUENCE {
	matchingUeCondList			MatchingUeCondPerSubList-v300,
	subscriptionInfo				E2SM-KPM-ActionDefinition-Format1-v300,
	...
}

E2SM-KPM-ActionDefinition-Format5-v300 ::= SEQUENCE {
	matchingUEidList				MatchingUEidPerSubList,
	subscriptionInfo				E2SM-KPM-ActionDefinition-Format1-v300,
	...
}
	
-- **************************************************************
--	Indication Header OCTET STRING contents
-- **************************************************************
	
E2SM-KPM-IndicationHeader ::= SEQUENCE{
    indicationHeader-formats	CHOICE{
        indicationHeader-Format1	E2SM-KPM-IndicationHeader-Format1,
        ...
    },
    ...
}
	
E2SM-KPM-IndicationHeader-Format1 ::= SEQUENCE{
    colletStartTime	    TimeStamp,
    fileFormatversion	PrintableString (SIZE (0..15), ...)	    OPTIONAL,
    senderName	        PrintableString (SIZE (0..400), ...)    OPTIONAL,
    senderType	        PrintableString (SIZE (0..8), ...)	    OPTIONAL,
    vendorName	        PrintableString (SIZE (0..32), ...)	    OPTIONAL,
    ...
}

E2SM-KPM-IndicationHeader-v300 ::= SEQUENCE{
	indicationHeader-formats		CHOICE{
		indicationHeader-Format1		E2SM-KPM-IndicationHeader-Format1-v300,
		...
	},
	...
}

E2SM-KPM-IndicationHeader-Format1-v300 ::= SEQUENCE{
	colletStartTime				TimeStamp-v300,
	fileFormatversion				PrintableString (SIZE (0..15), ...)		OPTIONAL,
	senderName						PrintableString (SIZE (0..400), ...)	OPTIONAL,
	senderType						PrintableString (SIZE (0..8), ...)		OPTIONAL,
	vendorName						PrintableString (SIZE (0..32), ...)		OPTIONAL,
	...
}
-- **************************************************************
--	Indication Message OCTET STRING contents
-- **************************************************************

E2SM-KPM-IndicationMessage ::= SEQUENCE{
    indicationMessage-formats	CHOICE{
        indicationMessage-Format1	E2SM-KPM-IndicationMessage-Format1,
        indicationMessage-Format2	E2SM-KPM-IndicationMessage-Format2,
        ...,
        indicationMessage-Format3	E2SM-KPM-IndicationMessage-Format3
    },
    ...
}

E2SM-KPM-IndicationMessage-Format1 ::= SEQUENCE {
    measData	    MeasurementData,
    measInfoList	MeasurementInfoList	OPTIONAL,
    granulPeriod	GranularityPeriod	OPTIONAL,
    ...
}

E2SM-KPM-IndicationMessage-Format2 ::= SEQUENCE {
    measData	        MeasurementData,
    measCondUEidList	MeasurementCondUEidList,
    granulPeriod	    GranularityPeriod	        OPTIONAL,
    ...
}

E2SM-KPM-IndicationMessage-Format3 ::= SEQUENCE {
    ueMeasReportList	UEMeasurementReportList,
    ...
}


E2SM-KPM-IndicationMessage-v300 ::= SEQUENCE{
	indicationMessage-formats		CHOICE{
		indicationMessage-Format1		E2SM-KPM-IndicationMessage-Format1-v300,
		indicationMessage-Format2		E2SM-KPM-IndicationMessage-Format2-v300,
		...,
		indicationMessage-Format3		E2SM-KPM-IndicationMessage-Format3-v300
	},
	...
}

E2SM-KPM-IndicationMessage-Format1-v300 ::= SEQUENCE {
	measData							MeasurementData,
	measInfoList					MeasurementInfoList-v300						OPTIONAL,
	granulPeriod					GranularityPeriod 						OPTIONAL,
	...
}

E2SM-KPM-IndicationMessage-Format2-v300 ::= SEQUENCE {
	measData							MeasurementData,
	measCondUEidList				MeasurementCondUEidList-v300,
	granulPeriod					GranularityPeriod 						OPTIONAL,
	...
}

E2SM-KPM-IndicationMessage-Format3-v300 ::= SEQUENCE {
	ueMeasReportList				UEMeasurementReportList-v300,
	...
}


-- ***************************************************************
--	RAN Function Definition OCTET STRING contents
-- ***************************************************************

E2SM-KPM-RANfunction-Description ::= SEQUENCE{
    ranFunction-Name	        RANfunction-Name,
    ric-EventTriggerStyle-List	SEQUENCE (SIZE(1..maxnoofRICStyles)) OF RIC-EventTriggerStyle-Item	OPTIONAL,
    ric-ReportStyle-List	    SEQUENCE (SIZE(1..maxnoofRICStyles)) OF RIC-ReportStyle-Item	OPTIONAL,
    ...
}

E2SM-KPM-RANfunction-Description-v300 ::= SEQUENCE{
	ranFunction-Name					RANfunction-Name,
	ric-EventTriggerStyle-List		SEQUENCE (SIZE(1..maxnoofRICStyles)) OF RIC-EventTriggerStyle-Item 		OPTIONAL,
	ric-ReportStyle-List				SEQUENCE (SIZE(1..maxnoofRICStyles)) OF RIC-ReportStyle-Item-v300 				OPTIONAL,
	...
}

RIC-EventTriggerStyle-Item ::= SEQUENCE{
    ric-EventTriggerStyle-Type	RIC-Style-Type,
    ric-EventTriggerStyle-Name	RIC-Style-Name,
    ric-EventTriggerFormat-Type	RIC-Format-Type,
    ...
}

RIC-ReportStyle-Item ::= SEQUENCE{
    ric-ReportStyle-Type	            RIC-Style-Type,
    ric-ReportStyle-Name	            RIC-Style-Name,
    ric-ActionFormat-Type	            RIC-Format-Type,
    measInfo-Action-List	            MeasurementInfo-Action-List,
    ric-IndicationHeaderFormat-Type	    RIC-Format-Type,
    ric-IndicationMessageFormat-Type	RIC-Format-Type,
    ...
}

RIC-ReportStyle-Item-v300 ::= SEQUENCE{
	ric-ReportStyle-Type						RIC-Style-Type,
	ric-ReportStyle-Name						RIC-Style-Name,
	ric-ActionFormat-Type					RIC-Format-Type,
	measInfo-Action-List						MeasurementInfo-Action-List-v300, 
	ric-IndicationHeaderFormat-Type		RIC-Format-Type,
	ric-IndicationMessageFormat-Type		RIC-Format-Type,
	...
}

END

-- ASN1STOP

```
:::

After merged, update the codec by this [user guide](https://hackmd.io/ToTtUyusT6e31BVfMdgB2A).

Modify E2SM-KPM handler to support ver.3 in different functions. 

### 4.14 KPM xApp subscribes according to DB columns

To make a different to KPIMON-GO xApp. KPM xApp needs to support subscribes according to DB columns. Here are 3 steps to be developed:

1. Encode action definition from action item in E2 Setup Request: in the past, action definition are got in hard core because the programming are crush and can't find the bug. We modify the coding architecture. Encoding part will be finished as much as possible in C langauge. (Wrapper.c)
- Wrapper.c
```c=
ssize_t Encode_Action_Definition_Format_1_in_C(void *Buffer, size_t Buf_Size, void *measName, void *measNameLen, size_t sizeOfMeasName){
    // fprintf(stderr, "[Wrapper.c] INFO --> Jacky, Enter %s\n", __func__);

    // uint8_t cellID[] = "000100100011010001010110000000000001";
    uint8_t plmnID[] = {0x00, 0x1F, 0x01};
    char (*measNamePtr)[25] = (char (*)[25])measName;
    int *measNameLenPtr = (int*)measNameLen;
    
    E2SM_KPM_ActionDefinition_t *actionDefini;
    actionDefini = (E2SM_KPM_ActionDefinition_t *)calloc(1, sizeof(E2SM_KPM_ActionDefinition_t));
    E2SM_KPM_ActionDefinition_Format1_t *actionDefiniFmt1;
    actionDefiniFmt1 = (E2SM_KPM_ActionDefinition_Format1_t *)calloc(1, sizeof(E2SM_KPM_ActionDefinition_Format1_t));
    MeasurementInfoItem_t *measInfoItem = (MeasurementInfoItem_t*)calloc(sizeOfMeasName, sizeof(MeasurementInfoItem_t));
    CGI_t *cgi = (CGI_t*)calloc(1, sizeof(CGI_t));
    NR_CGI_t *nrcgi = (NR_CGI_t*)calloc(1, sizeof(NR_CGI_t));
    nrcgi->pLMNIdentity.buf = (uint8_t*)calloc(3, sizeof(uint8_t));
    nrcgi->nRCellIdentity.buf = (uint8_t*)calloc(5, sizeof(uint8_t));
    nrcgi->nRCellIdentity.size = 5;
    nrcgi->nRCellIdentity.bits_unused = 4;

    if(!actionDefini){
        fprintf(stderr,"Failed to allocate memory for E2SM_KPM_ActionDefinition_t\n") ;
        return -1;
    }

    actionDefini->ric_Style_Type = 1;
    actionDefini->actionDefinition_formats.present = E2SM_KPM_ActionDefinition__actionDefinition_formats_PR_actionDefinition_Format1;
    actionDefini->actionDefinition_formats.choice.actionDefinition_Format1 = actionDefiniFmt1;
    actionDefiniFmt1->granulPeriod = 1;
    actionDefiniFmt1->cellGlobalID = cgi;

    cgi->present = CGI_PR_nR_CGI;
    cgi->choice.nR_CGI = nrcgi;
    fillBitString(&nrcgi->nRCellIdentity, 4, 5, 104393985);

    nrcgi->pLMNIdentity.size = 3;
    memcpy(nrcgi->pLMNIdentity.buf, plmnID, 3);
    
    for(int i=0;i<sizeOfMeasName;i++){
        measInfoItem[i].measType.present = MeasurementType_PR_measName;
        measInfoItem[i].measType.choice.measName.size = measNameLenPtr[i];
        measInfoItem[i].measType.choice.measName.buf = (uint8_t*)calloc(measNameLenPtr[i], sizeof(uint8_t));
        memcpy(measInfoItem[i].measType.choice.measName.buf, measNamePtr[i], measNameLenPtr[i]);
        ASN_SEQUENCE_ADD(&actionDefiniFmt1->measInfoList.list, &measInfoItem[i]);
    }

    xer_fprint(stderr,  &asn_DEF_E2SM_KPM_ActionDefinition, actionDefini);

    asn_enc_rval_t Result;
    Result = aper_encode_to_buffer(&asn_DEF_E2SM_KPM_ActionDefinition, NULL, actionDefini, Buffer, Buf_Size);

    if(Result.encoded == -1) {
        fprintf(stderr, "Can't encode %s: %s\n", Result.failed_type->name, strerror(errno));
        return -1;
    } else {
	    return Result.encoded;
	}

    return 0;
}

ssize_t Encode_Action_Definition_Format_3_in_C(void *Buffer, size_t Buf_Size, void *measName, void *measNameLen, size_t sizeOfMeasName){
    uint8_t plmnID[] = {0x00, 0x1F, 0x01};
    char (*measNamePtr)[25] = (char (*)[25])measName;
    int *measNameLenPtr = (int*)measNameLen;
    
    E2SM_KPM_ActionDefinition_t *actionDefini;
    actionDefini = (E2SM_KPM_ActionDefinition_t *)calloc(1, sizeof(E2SM_KPM_ActionDefinition_t));
    E2SM_KPM_ActionDefinition_Format3_t *actionDefiniFmt3;
    actionDefiniFmt3 = (E2SM_KPM_ActionDefinition_Format3_t *)calloc(1, sizeof(E2SM_KPM_ActionDefinition_Format3_t));
    MeasurementCondItem_t *measCondItem = (MeasurementCondItem_t*)calloc(sizeOfMeasName, sizeof(MeasurementCondItem_t));
    CGI_t *cgi = (CGI_t*)calloc(1, sizeof(CGI_t));
    NR_CGI_t *nrcgi = (NR_CGI_t*)calloc(1, sizeof(NR_CGI_t));
    nrcgi->pLMNIdentity.buf = (uint8_t*)calloc(3, sizeof(uint8_t));
    nrcgi->nRCellIdentity.buf = (uint8_t*)calloc(5, sizeof(uint8_t));
    nrcgi->nRCellIdentity.size = 5;
    nrcgi->nRCellIdentity.bits_unused = 4;

    if(!actionDefini){
        fprintf(stderr,"Failed to allocate memory for E2SM_KPM_ActionDefinition_t\n") ;
        return -1;
    }

    actionDefini->ric_Style_Type = 3;
    actionDefini->actionDefinition_formats.present = E2SM_KPM_ActionDefinition__actionDefinition_formats_PR_actionDefinition_Format3;
    actionDefini->actionDefinition_formats.choice.actionDefinition_Format3 = actionDefiniFmt3;
    actionDefiniFmt3->granulPeriod = 1;
    actionDefiniFmt3->cellGlobalID = cgi;

    cgi->present = CGI_PR_nR_CGI;
    cgi->choice.nR_CGI = nrcgi;
    fillBitString(&nrcgi->nRCellIdentity, 4, 5, 104393985);

    nrcgi->pLMNIdentity.size = 3;
    memcpy(nrcgi->pLMNIdentity.buf, plmnID, 3);
    
    for(int i=0;i<sizeOfMeasName;i++){
        measCondItem[i].measType.present = MeasurementType_PR_measName;
        measCondItem[i].measType.choice.measName.size = measNameLenPtr[i];
        measCondItem[i].measType.choice.measName.buf = (uint8_t*)calloc(measNameLenPtr[i], sizeof(uint8_t));
        memcpy(measCondItem[i].measType.choice.measName.buf, measNamePtr[i], measNameLenPtr[i]);
        ASN_SEQUENCE_ADD(&actionDefiniFmt3->measCondList.list, &measCondItem[i]);
    }

    xer_fprint(stderr,  &asn_DEF_E2SM_KPM_ActionDefinition, actionDefini);

    asn_enc_rval_t Result;
    Result = aper_encode_to_buffer(&asn_DEF_E2SM_KPM_ActionDefinition, NULL, actionDefini, Buffer, Buf_Size);

    if(Result.encoded == -1) {
        fprintf(stderr, "Can't encode %s: %s\n", Result.failed_type->name, strerror(errno));
        return -1;
    } else {
	    return Result.encoded;
	}

    return 0;
}
```
2. Get columns name in InfluxDB: Call API to get influxdb columns:
```go=

func getCellMetricsName() {
	// Send GET request
	response, err := http.Get("http://ricplt-influxdb.ricplt:8086/query?u=admin&p=UwuVmf6Tha&db=kpm&q=SELECT%20*%20FROM%20CellMetrics")
	if err != nil {
		xapp.Logger.Info("Error sending request:", err)
	}

	defer response.Body.Close()

	// Read response body
	body, err := ioutil.ReadAll(response.Body)
	if err != nil {
		xapp.Logger.Info("Error reading response:", err)
	}

	// Parse the JSON response
	var data Result
	if err := json.Unmarshal(body, &data); err != nil {
		xapp.Logger.Info("Error parsing JSON:", err)
	}

	// Extract the column names
	columnNames := data.Results[0].Series[0].Columns

	// Remove the "time" and "RanName" elements from the slice
	for _, col := range columnNames {
		if col != "time" && col != "RanName" {
			cellMetricsInfo = append(cellMetricsInfo, col)
		}
	}

	// Print the column names
	xapp.Logger.Info("cell Metrics Name: %v", cellMetricsInfo)
}
```
3. Support writing InfluxDB dynamiclly
==Ongoing(6/7)==


## 5. Result


