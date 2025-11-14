1. ---
tags: 【xApp】
---
# 【G Release】 Integrate and Test TS Use Case
:::info
- goal
	- Integate KPIMON-GO xApp, TS xApp, QP xApp, AD xApp and RC xApp to lab server.
- reference
	- [[F Release] Integrate and Test Traffic Steering (TS) Use Case](https://hackmd.io/@Winnie27/BJKdplS69)
	- [InfluxDB2](https://influxdb-client.readthedocs.io/en/latest/)
	- [Python xApp framework source code](https://gerrit.o-ran-sc.org/r/gitweb?p=ric-plt%2Fxapp-frame-py.git;a=shortlog;h=refs%2Fheads%2Fmaster)
	- [Python xApp framework document](https://docs.o-ran-sc.org/projects/o-ran-sc-ric-plt-xapp-frame-py/en/latest/)
	- [InfluxDB2 Writting](https://influxdb-client.readthedocs.io/en/v1.2.0/usage.html#write)
	- [InfluxDB2 Group](https://docs.influxdata.com/flux/v0.x/get-started/data-model/)
	- [InfluxDB-InfluxDB-v2-User-Guide](https://hackmd.io/@Yueh-Huan/rkldH-FEh#InfluxDB-InfluxDB-v2-User-Guide)
:::
---
## 1. Introduce
### 1.1 Goal of TS Use Case
- The goal of the TS use case is to implement QoE-based traffic steering, where user experience is improved by intelligently steering traffic among multiple cells, via a closed-loop UE-level performance monitoring and control. The proposed solution leverages predictive analytics and algorithms to provide UE-level performance monitoring and optimization, utilizing near real-time data.
- For the purpose of this use case, QoE is measured as average UE PDCP throughput, averaged over a certain temporal window whose size can controlled by a parameter. The QoE metric itself can be potentially configured via A1 policy for example. The objective function of this use case is to maximize the QoE improvement of the worst-performing priority traffic.
### 1.2 System Architecture of TS Use Case in E release
#### 1.2.1 Platform Component of TS Use case
**E2 Manager:**
- E2 Manager is to manage, verify, and allow E2 Node connection. Moreover, it also address E2 related procedure (e.g. E2Setup, E2NodeConfigurationUpdate, E2Reset...). It will gather and collect the messages(e.g. E2 Node ID, support RAN  function...) sended by E2 Termination and write them into R-NIB.

**Redis DB:**
- Redis（Remote Dictionary Server）DB is a key-value format database. It implements R-NIB and stores data which are not time series in OSC.

**Subscription Manager:**
- Subscription Manager is to manage subscription between xApp and E2 Node.
	- Lesten xApp subscription from Restful API
	- xApp can request, query and delete subscription.
	- If Subscription Manager receives same subscription from different xApps, it will merge them.
	- Encode xApp subscription message to E2 subscription request format and sent to E2 Node through E2 termination.
	- Notify xApp wether subscription is success.

**InfluxDB:**
- The InfluxDB is a time series database (TSDB) from InfluxData.
	- Time series data can be analyzed and evaluated from the past few pieces of data to see the correlation between them.

**E2 Termination:**
- The E2 Termination supports the following functions：
	- Open or remove SCTP Connection upon E2/EN-DC Setup or Removal.
	- Handle own repository to map RAN to SCTP Connection.
	- Listen to all its SCTP Connection. Upon E2 method, decode it and sends it over the RMR to the relevant xApp.
	- Listen to the RMR Connection. Upon on RMR Request, convert it to E2AP, map the target RAN to SCTP Connection, decode it and sends it over the relevant SCTP.
#### 1.2.2 xApp of TS Use case
**KPIMON-GO xApp:**
- Kpimon(Key Performance Monitor)-GO xApp is to collect E2 Node metrics from E2 Node following E2 SM KPI and store them into influxDB.

**AD xApp:**
- The AD xApp is an xApp in the Traffic Steering O-RAN use case, which perfrom the following tasks：
	- Data will be inserted into influxDB when xApp starts. This will be removed in Future when data will be coming via KPIMON to influxDB.
	- AD xApp iterates per 10 mili-second, fetches UE information from databse and Detect Anomulous UE’s and send those UE’s information to TS xApp.

**TS xApp:**
- TS xApp is the pivot xApp of TS Use Case, it will make the final decision.
- TS xApp has the following functions：
	- Receives A1 policy
	- Receives anomaly detection
	- Requests prediction for UE throughput on current and Receives prediction
	- Optionally exercises Traffic Steering action over E2

**QP xApp:**
- The QP xApp is an application that forecast throughput in next few timestamps in advance for a given user and its cells.

**RC xApp:**
- The RC xapp is deployed on RIC Platform and provides the basic implementation of initiating spec compliant E2-SM RC based RIC Control Request message to RAN/E2 Node based on the GRPC control request received from other xapps.

## 2. Test Environment
### 2.1 Computer Operation
| Test Environment | G Release          |
| ---------------- | ------------------ |
| Operating System | Ubuntu 20.04.4 LTS |

### 2.2 K8S, docker and helm Version
| K8S     |          docker           | helm   |
| ------- |:-------------------------:| ------ |
| v1.16.0 | 20.10.12-0ubuntu2~20.04.1 | v3.5.4 |

### 2.3 Related Platform Component Version
| Component            | Version      |
| -------------------- | ------------ |
| A1 Mediator          | 3.0.1        |
| xApp Manager         | 0.5.7        |
| E2 Manager           | 6.0.1        |
| Subscription Manager | 0.9.5        |
| Routing Manager      | 0.9.4        |
| E2 Termination       | 6.0.1        |
| InfluxDB             | 2.2.0-alpine |
| DBaaS                | 0.6.2        |

- Some pod need to be revise for VIAVI RIC TEST: 
  - https://hackmd.io/@Kenny-Lai/SkZCi4vC3#1-2-Version

### 2.4 TS Use Case xApp Version
| xApp Component | Image fo Version | Modified |
|:--------------:|:----------------:|:--------:|
|       TS       |      1.2.5       |    ⭕    |
|       AD       |      1.0.0       |    ⭕    |
|       QP       |      0.0.5       |    ⭕    |
|   KPIMON-GO    |      1.0.1       |    ⭕    |
|       RC       |      1.0.4       |    ❌    |


## 3. Message
### 3.1 Routing Path of TS Use Case
#### **RMR:**
|       Message       | Message Type | Direction |
|:-------------------:|:------------:|:---------:|
|   RIC_CONTROL_REQ   |    12040     |  RC xApp -> E2 Termination         |
|   RIC_CONTROL_ACK   |    12041     |  E2 Termination -> RC xApp         |
| RIC_CONTROL_FAILURE |    12042     |  E2 Termination -> RC xApp         |
|   RIC_INDICATION    |    12050     |  E2 Termination -> KPIMON-GO xApp         |
|    A1_POLICY_REQ    |    20010     |  A1 Mediator -> TS xApp         |
|     TS_UE_LIST      |    30000     |  TS xApp -> QP xApp         |
|  TS_QOE_PREDICTION  |    30002     |  QP xApp -> TS xApp         |
|  TS_ANOMALY_UPDATE  |    30003     |  AD xApp -> TS xApp    |
|   TS_ANOMALY_ACK    |    30004     |  TS xApp -> AD xApp         |

#### **GRPC:**
* IP:Port of RC xApp：service-ricxapp-rc-grpc-server.ricxapp.svc.cluster.local:7777

|            Message            |     Direction      |
|:-----------------------------:|:------------------:|
| Parameters of Control Request | TS xApp -> RC xApp |
| ACK Success/Failure  Response | RC xApp -> TS xApp |

#### **REST:**
Integrates with VIAVI Simulator (and others).

### 3.2 Message Flow of TS Use case
<iframe frameborder="0" style="width:100%;height:1228px;" src="https://viewer.diagrams.net/?tags=%7B%7D&highlight=0000ff&edit=_blank&layers=1&nav=1&title=TS%20Use%20Case.drawio#Uhttps%3A%2F%2Fdrive.google.com%2Fuc%3Fid%3D1jO2WXU0FJH-VXCyKUplLTVluWPHQpUSM%26export%3Ddownload"></iframe>

### 3.3 MSC of TS Use case
![](https://hackmd.io/_uploads/BJjLxovon.png)



---
## 4. Useful command
### 4.1 Set chartmuseum environment variable
- If there are port-forwarding.
- ![](https://hackmd.io/_uploads/B1XWVHFV3.png)
```shell=
export CHART_REPO_URL=http://0.0.0.0:8090
```
- Otherwise
```shell=
export NODE_PORT=$(kubectl get --namespace ricinfra -o jsonpath="{.spec.ports[0].nodePort}" services r4-chartmuseum-chartmuseum)
export NODE_IP=$(kubectl get nodes --namespace ricinfra -o jsonpath="{.items[0].status.addresses[0].address}")
export CHART_REPO_URL=http://$NODE_IP:$NODE_PORT/charts
```
### 4.2 Commad adout xApp onboard/deploy/undeploy
#### 4.2.1 Commands of xApp onboarding
```shell=
dms_cli onboard --config_file_path=<CONFIG_FILE_PATH> --shcema_file_path=<SCHEMA_FILE_PATH>
```
#### 4.2.2 Commands of downloading the xApp helm charts
```shell=
dms_cli download_helm_chart --xapp_chart_name=<XAPP_CHART_NAME> --version=<VERSION> --output_path=<OUTPUT_PATH>
```
#### 4.2.3 Commands of xApp deploying (1)
- Deploy xApp by using helm chart of helm repository
 ```shell=
 dms_cli install --xapp_chart_name=<XAPP_CHART_NAME> --version=<VERSION> --namespace=<NAMESPACE>
```
#### 4.2.4 Commands of xApp deploying (2)
- Deploy xApp by using helm charts which is providing the override values.yaml
	1. **Download the default values.yaml**
		```shell=
		dms_cli download_values_yaml --xapp_chart_name=<XAPP_CHART_NAME> --version=<VERSION> --output_path=<OUTPUT_PATH>
		```
	2. Modify values.yaml and provide it as override file**
        ```shell=
		dms_cli install --xapp_chart_name=<XAPP_CHART_NAME> --version=<VERSION> --namespace=<NAMESPACE> --overridefile=<OVERRIDEFILE>
		```
#### 4.2.5 Commands of xApp undeploying
```shell=
dms_cli uninstall --xapp_chart_name=<XAPP_CHART_NAME> --namespace=<NAMESPACE>
```
#### 4.2.6 Commands of xApp upgrading：
```shell=
dms_cli upgrade --xapp_chart_name=<XAPP_CHART_NAME> --old_version=<OLD_VERSION> --new_version=<NEW_VERSION> --namespace=<NAMESPACE>
```
#### 4.2.7 Commands of xApp rollbacking：
```shell=
dms_cli rollback --xapp_chart_name=<XAPP_CHART_NAME> --new_version=<NEW_VERSION> --old_version=<OLD_VERSION> --namespace=<NAMESPACE>
```
#### 4.2.8 Commands of xApp health checking：
```shell=
dms_cli health_check --xapp_chart_name=<XAPP_CHART_NAME> --namespace=<NAMESPACE>
```

### 4.3 Commands about helm charts
#### 4.3.1 List all the helm charts from helm repository
```shell=
dms_cli get_charts_list
```
#### 4.3.2 Delete a specific Chart Version from helm repository
```shell=
curl -X DELETE $(CHART_REPO_URL)/api/charts/<XAPP_CHART_NAME>/<VERSION>
```
### 4.4 Query connection nodeB status
```shell=
curl -s -X GET http://$(kubectl get svc -A| grep e2mgr|grep 3800|awk '{print $4}'):3800/v1/nodeb/states | jq .
```
### 4.5 InfluxDB query
```shell=
kubectl exec -it $(kubectl get pods -A | grep infl | awk '{print $2}') -n ricplt /bin/sh
```
### 4.6 Query routing table
```shell=
curl -X GET "http://$(kubectl get svc -A|grep rtmgr|grep 3800|awk '{print $4}'):3800/ric/v1/getdebuginfo" -H "accept: application/json" | jq .
```

---

## 5. Test the TS Use Case
### 5.1 QP xApp deployment
#### 5.1.1 Download QP source code 
```shell=
git clone "https://github.com/o-ran-sc/ric-app-qp.git" -b g-release
cd ric-app-qp
```
#### 5.1.2 [Revise QP xApp source code](https://hackmd.io/@2xIzdkQiS9K3Pfrv6tVEtA/SkfaJhoq3)
#### 5.1.3 Build image
```shell=
docker build -t nexus3.o-ran-sc.org:10002/o-ran-sc/ric-app-qp:0.0.5 .
```
#### 5.1.4 Onboard QP xApp
```shell=
dms_cli onboard --config_file_path=xapp-descriptor/config.json --shcema_file_path=xapp-descriptor/schema.json
```
#### 5.1.5 Deploying QP xApp
```shell=
dms_cli install --xapp_chart_name=qp --version=0.0.5 --namespace=ricxapp
```
#### 5.1.6 Check xApp information
```shell=
kubectl get all -n ricxapp |grep qp
kubectl logs -n $(kubectl get pods -A |grep ricxapp-qp|awk '{print $1 " " $2}')
kubectl logs -n ricplt $(kubectl get pods -A|grep appmgr|awk '{print $2}')|grep qp
```

#### 5.1.7 Deregister & uninstall QP xApp(If you want to uninstall)
```shell=
curl -X 'POST' "http://$(kubectl get svc -A|grep appmgr|grep 8080|awk '{print $4}'):8080/ric/v1/deregister" -H 'accept: application/json' -H 'Content-Type: application/json' -d '{
"appName": "qp",
"appInstanceName": "qp"
}'
dms_cli uninstall --xapp_chart_name=qp --namespace=ricxapp
curl -X DELETE http://0.0.0.0:8090/api/charts/qp/0.0.5
```
### 5.2 AD xApp deployment
#### 5.2.1 Download AD source code 
```shell=
git clone https://github.com/o-ran-sc/ric-app-ad.git -b g-release
cd ric-app-ad
``` 
#### 5.2.2 [Revise AD xApp source code](https://hackmd.io/@2xIzdkQiS9K3Pfrv6tVEtA/SJvbON0c2)

#### 5.2.3 Build image
```shell=
docker build -t nexus3.o-ran-sc.org:10002/o-ran-sc/ric-app-ad:1.0.0 .
```
#### 5.2.4 Onboard AD xApp
```shell=
dms_cli onboard --config_file_path=xapp-descriptor/config.json --shcema_file_path=xapp-descriptor/schema.json
```
#### 5.2.5 Deploying AD xApp
```shell=
dms_cli install --xapp_chart_name=ad --version=1.0.0 --namespace=ricxapp
```
#### 5.2.6 Check xApp information
```shell=
kubectl get all -n ricxapp |grep ad
kubectl logs -n $(kubectl get pods -A |grep ricxapp-ad|awk '{print $1 " " $2}')
kubectl logs -n ricplt $(kubectl get pods -A|grep appmgr|awk '{print $2}')|grep qp
```
#### 5.2.7 Deregister & uninstall AD xApp(If you want to uninstall)
```shell=
curl -X 'POST' "http://$(kubectl get svc -A|grep appmgr|grep 8080|awk '{print $4}'):8080/ric/v1/deregister" -H 'accept: application/json' -H 'Content-Type: application/json' -d '{
"appName": "ad",
"appInstanceName": "ad"
}'
dms_cli uninstall --xapp_chart_name=ad --namespace=ricxapp
curl -X DELETE http://0.0.0.0:8090/api/charts/ad/1.0.0
```
### 5.3 TS xApp deployment
#### 5.3.1 Download TS source code 
```shell=
git clone https://github.com/o-ran-sc/ric-app-ts.git -b g-release
cd ric-app-ts
``` 
#### 5.3.2 [Revise TS xApp source code](https://hackmd.io/@2xIzdkQiS9K3Pfrv6tVEtA/SJwnzngoh)
#### 5.3.3 Build image
```shell=
docker build -t nexus3.o-ran-sc.org:10002/o-ran-sc/ric-app-ts:1.2.5 .
```
#### 5.3.4 Onboard TS xApp
```shell=
dms_cli onboard --config_file_path=xapp-descriptor/config-file.json --shcema_file_path=xapp-descriptor/schema.json
```
#### 5.3.5 Deploying TS xApp
```shell=
dms_cli install --xapp_chart_name=trafficxapp --version=1.2.5 --namespace=ricxapp
```
#### 5.3.6 Register TS xApp
```shell=
export Service_TS=$(kubectl get services -n ricxapp | grep "\-trafficxapp\-" | cut -f1 -d ' ')
export TS_IP=$(kubectl get svc ${Service_TS} -n ricxapp -o yaml | grep clusterIP | awk '{print $2}')

curl -X POST "http://$(kubectl get svc -A|grep appmgr|grep 8080|awk '{print $4}'):8080/ric/v1/register" -H 'accept: application/json' -H 'Content-Type: application/json' -d '{
  "appName": "trafficxapp",
  "appVersion": "1.2.5",
  "appInstanceName": "trafficxapp",
  "httpEndpoint": "",
  "rmrEndpoint": "${TS_IP}:4560",
  "config": " {\n    \"name\": \"trafficxapp\",\n    \"version\": \"1.2.5\",\n    \"containers\": [{\"image\":{\"name\":\"o-ran-sc/ric-app-ts\",\"registry\":\"nexus3.o-ran-sc.org:10002\",\"tag\":\"1.2.5\"},\"name\":\"trafficxapp\"}],\n    \"messaging\": {\n        \"ports\": [{\"container\":\"trafficxapp\",\"description\":\"rmr route port for trafficxapp xapp\",\"name\":\"rmr-route\",\"port\":4561},{\"container\":\"trafficxapp\",\"description\":\"rmr receive data port for trafficxapp\",\"name\":\"rmr-data\",\"policies\":[20008],\"port\":4560,\"rxMessages\":[\"TS_QOE_PREDICTION\",\"A1_POLICY_REQ\",\"TS_ANOMALY_UPDATE\"],\"txMessages\":[\"TS_UE_LIST\",\"TS_ANOMALY_ACK\"]}]\n    },\n    \"rmr\": {\n        \"protPort\": \"tcp:4560\",\n        \"maxSize\": 2072,\n        \"numWorkers\": 1,\n        \"txMessages\": [\"TS_UE_LIST\",\"TS_ANOMALY_ACK\"],\n        \"rxMessages\": [\"TS_QOE_PREDICTION\",\"A1_POLICY_REQ\",\"TS_ANOMALY_UPDATE\"],\n        \"policies\": [20008]\n    },\n    \"controls\": {\n        \"ts_control_api\": \"grpc\",\n        \"ts_control_ep\": \"service-ricxapp-rc-grpc-server.ricxapp.svc.cluster.local:7777\"\n    }\n    \n}\n"}  "
}'
```
#### 5.3.7 Check TS xApp information
```shell=
kubectl get all -n ricxapp |grep trafficxapp
kubectl logs -n $(kubectl get pods -A |grep trafficxapp| awk '{print $1 " " $2}')
kubectl logs -n ricplt $(kubectl get pods -A|grep appmgr|awk '{print $2}')
```
#### 5.3.8 Deregister & uninstall TS xApp(If you want to uninstall)
```shell=
curl -X 'POST' "http://$(kubectl get svc -A|grep appmgr|grep 8080|awk '{print $4}'):8080/ric/v1/deregister" -H 'accept: application/json' -H 'Content-Type: application/json' -d '{
"appName": "trafficxapp",
"appInstanceName": "trafficxapp"
}'
dms_cli uninstall --xapp_chart_name=trafficxapp --namespace=ricxapp
curl -X DELETE http://0.0.0.0:8090/api/charts/trafficxapp/1.2.5
```
### 5.4 KPIMON-GO xApp deployment
#### 5.4.1 Download KPIMON-GO source code 
```shell=
git clone https://github.com/o-ran-sc/ric-app-kpimon-go.git -b g-release
cd ric-app-kpimon-go
``` 
#### 5.4.2 [Revise KPIMON-GO xApp source code](https://hackmd.io/@Kenny-Lai/HJT1JMTq3)
#### 5.4.3 Build image
```shell=
docker build -t nexus3.o-ran-sc.org:10004/o-ran-sc/ric-app-kpimon-go:1.0.1 .
```
#### 5.4.4 Onboard KPIMON-GO xApp
```shell=
dms_cli onboard --config_file_path=deploy/config.json --shcema_file_path=deploy/schema.json
```
#### 5.4.5 Deploying KPIMON-GO xApp
```shell=
dms_cli install --xapp_chart_name=kpimon-go --version=2.0.1 --namespace=ricxapp
```
#### 5.4.6 Check KPIMON-GO xApp information
```shell=
kubectl get all -n ricxapp |grep kpimon
kubectl logs -n $(kubectl get pods -A |grep kpimon| awk '{print $1 " " $2}')
kubectl logs -n ricplt $(kubectl get pods -A|grep appmgr|awk '{print $2}')
```
#### 5.4.7 Deregister & uninstall KPIMON-GO xApp(If you want to uninstall)
```shell=
curl -X 'POST' "http://$(kubectl get svc -A|grep appmgr|grep 8080|awk '{print $4}'):8080/ric/v1/deregister" -H 'accept: application/json' -H 'Content-Type: application/json' -d '{
"appName": "kpimon-go",
"appInstanceName": "kpimon-go"
}'
dms_cli uninstall --xapp_chart_name=kpimon-go --namespace=ricxapp
curl -X DELETE http://0.0.0.0:8090/api/charts/kpimon-go/2.0.1
```

### 5.5 RC xApp deployment
#### 5.5.1 Download RC source code
```shell=
git clone "https://gerrit.o-ran-sc.org/r/ric-app/rc" -b g-release
cd rc/
```
#### 5.5.2 Build image
```shell=
docker build -t nexus3.o-ran-sc.org:10002/o-ran-sc/ric-app-rc:1.0.4 .
```
#### 5.5.3 Onboard RC xApp
```shell=
dms_cli onboard --config_file_path=xapp-descriptor/config.json --shcema_file_path=xapp-descriptor/schema.json
```
#### 5.5.4 Deploying RC xApp
```shell=
dms_cli install --xapp_chart_name=rc --version=1.0.0 --namespace=ricxapp
```

#### 5.5.5 Check RC xApp information
```shell=
kubectl get all -n ricxapp |grep rc
kubectl logs -n $(kubectl get pods -A |grep rc| awk '{print $1 " " $2}')
kubectl logs -n ricplt $(kubectl get pods -A|grep appmgr|awk '{print $2}')
```

#### 5.5.6 Deregister & uninstall RC xApp(If you want to uninstall)
```shell=
curl -X 'POST' "http://$(kubectl get svc -A|grep appmgr|grep 8080|awk '{print $4}'):8080/ric/v1/deregister" -H 'accept: application/json' -H 'Content-Type: application/json' -d '{
"appName": "rc",
"appInstanceName": "rc"
}'
dms_cli uninstall --xapp_chart_name=rc --namespace=ricxapp
curl -X DELETE 0.0.0.0:8090/api/charts/rc/1.0.0
```

---
## 6. InfluxDB v2 Setting
### 6.1 Configuration
#### 6.1.1 Check platform configuration
- Connect to InfluxDB Pod:
```bash=
kubectl exec -it -n ricplt $(kubectl get pods -A | grep influx | awk '{print $2}') /bin/bash
```
or
```bash=
kubectl exec -it -n ricplt $(kubectl get pods -A | grep influx | awk '{print $2}') -- cat /var/lib/influxdb2/influxd.bolt | strings | grep "admin's Token" | grep token | awk -F'"token":"' '{print $2}' | awk -F'"' '{print $1}'
```
- Find InfluxDB2 Admin Token:
```bash=
cat /var/lib/influxdb2/influxd.bolt | strings | grep "admin's Token"
```
- result:
```shell=
0b7bf067c35f2000{"id":"0b7bf067c35f2000","token":"Kq28XHGrsUXjssxM1FyrchTuNSZOqSjT","status":"active","description":"admin's Token","orgID":"b9e6a853e2087e30","userID":"0b7bf067b15f2000","permissions":[{"action":"read","resource":{"type":"authorizations"}},{"action":"write","resource":{"type":"authorizations"}},{"action":"read","resource":{"type":"buckets"}},{"action":"write","resource":{"type":"buckets"}},{"action":"read","resource":{"type":"dashboards"}},{"action":"write","resource":{"type":"dashboards"}},{"action":"read","resource":{"type":"orgs"}},{"action":"write","resource":{"type":"orgs"}},{"action":"read","resource":{"type":"sources"}},{"action":"write","resource":{"type":"sources"}},{"action":"read","resource":{"type":"tasks"}},{"action":"write","resource":{"type":"tasks"}},{"action":"read","resource":{"type":"telegrafs"}},{"action":"write","resource":{"type":"telegrafs"}},{"action":"read","resource":{"type":"users"}},{"action":"write","resource":{"type":"users"}},{"action":"read","resource":{"type":"variables"}},{"action":"write","resource":{"type":"variables"}},{"action":"read","resource":{"type":"scrapers"}},{"action":"write","resource":{"type":"scrapers"}},{"action":"read","resource":{"type":"secrets"}},{"action":"write","resource":{"type":"secrets"}},{"action":"read","resource":{"type":"labels"}},{"action":"write","resource":{"type":"labels"}},{"action":"read","resource":{"type":"views"}},{"action":"write","resource":{"type":"views"}},{"action":"read","resource":{"type":"documents"}},{"action":"write","resource":{"type":"documents"}},{"action":"read","resource":{"type":"notificationRules"}},{"action":"write","resource":{"type":"notificationRules"}},{"action":"read","resource":{"type":"notificationEndpoints"}},{"action":"write","resource":{"type":"notificationEndpoints"}},{"action":"read","resource":{"type":"checks"}},{"action":"write","resource":{"type":"checks"}},{"action":"read","resource":{"type":"dbrp"}},{"action":"write","resource":{"type":"dbrp"}},{"action":"read","resource":{"type":"notebooks"}},{"action":"write","resource":{"type":"notebooks"}},{"action":"read","resource":{"type":"annotations"}},{"action":"write","resource":{"type":"annotations"}},{"action":"read","resource":{"type":"remotes"}},{"action":"write","resource":{"type":"remotes"}},{"action":"read","resource":{"type":"replications"}},{"action":"write","resource":{"type":"replications"}}],"createdAt":"2023-07-10T12:26:12.109498943Z","updatedAt":"2023-07-10T12:26:12.109498943Z"}
```
**token = Kq28XHGrsUXjssxM1FyrchTuNSZOqSjT**
- Create Config:
- Create a configuration for influxDB server in the influx cli.
```shell=
influx config create --config-name admin \
  --host-url http://localhost:8086 \
  --org influxdata \
  --token  BmHaJ9tkG7RSDZO2nsTeHyMPNT4MESZD\
  --active
```
- List User:
```shell=
influx user list
```
- Reset Password for Admin:
```shell=
influx user password --name admin --password 7jQCNdujbSKju7cL32IzOOwAx7rEjEGJ
```
:::warning
`http://192.168.8.220:32086/signin?returnTo=/orgs/af0b5b217ee7ca3b/data-explorer`
:::
#### 6.1.2 Enable External Access
```shell=
kubectl edit service -n ricplt r4-influxdb-influxdb2
```
```shell=
...
spec:
  clusterIP: 10.99.2.254
  externalTrafficPolicy: Cluster
  ports:
  - name: http
    nodePort: 32086                  # add
    port: 80
    protocol: TCP
    targetPort: 8086
  selector:
    app.kubernetes.io/instance: r4-influxdb
    app.kubernetes.io/name: influxdb2
  sessionAffinity: None
  type: NodePort                    # revise
```

## 7. Log and Issue
### 7.1 [KPIMON-GO <--> RIC Test](https://hackmd.io/@Kenny-Lai/SkZCi4vC3)