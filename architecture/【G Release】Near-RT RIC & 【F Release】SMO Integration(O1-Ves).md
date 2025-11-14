# 【G Release】Near-RT RIC & 【F Release】SMO Integration(O1-Ves)
###### tags: `Integration`
:::info
**Goal**
* Record the topology, steps and method to verify the integration.

**Main Reference**
* [[Rel-F or Rel-G] Near-RT RIC & [Rel-F] SMO Integration(O1-Ves)](https://hackmd.io/@Yueh-Huan/Hy3zx5m4h)
* [[G] O-DU sent VES Event to VES Collector](https://hackmd.io/lZK4w7EdTiyH-So34_FZRw?view#G-O-DU-sent-VES-Event-to-VES-Collector)

:::
## 1. Introduction

### 1-1 Detail component connection
![](https://hackmd.io/_uploads/BknyJvHq3.png)




### 1-2 Version
**【F Release】 SMO:**
* VES Collector: `nexus3.onap.org:10001/onap/org.onap.dcaegen2.collectors.ves.vescollector:1.11.0`

**【G Release】Near-RT RIC Platform:**
* VESPAmgr: `nexus3.o-ran-sc.org:10002/o-ran-sc/ric-plt-vespamgr:0.7.5`
* Prometheus: `prom/prometheus:v2.18.1`
* E2T: `nexus3.o-ran-sc.org:10002/o-ran-sc/ric-plt-e2:6.0.1`

### 1-3 MSC(Message Sequence Chart)
![](https://hackmd.io/_uploads/BkqO8d_C2.png)


## 2. Configuration
### 2-1 Near-RT RIC: VESPAmgr
**Edit Configuration:**
```shell=
# Download and Revise source code
cd ~
git clone "https://gerrit.o-ran-sc.org/r/ric-plt/vespamgr" -b g-release
vim ~/vespamgr/config/config-file.json
```
```json=
 "controls": {
        "logger": {
            "level": 4
        },
        "host": "http://service-ricplt-vespamgr-http.ricplt.svc.cluster.local:8080",
        "measurementUrl": "/ric/v1/measurements",
        "pltFile": "/tmp/vespa-plt-meas.json",
        "pltCounterFile": "/cfg/plt-counter.json",
        "appManager": {
            "host": "http://service-ricplt-appmgr-http.ricplt.svc.cluster.local:8080",
            "path": "/ric/v1/config",
            "notificationUrl": "/ric/v1/xappnotif",
            "subscriptionUrl": "/ric/v1/subscriptions",
            "appmgrRetry": 100
        },
        "vesagent": {
            "configFile": "/etc/ves-agent/ves-agent.yaml",
            "hbInterval": "60s",
            "measInterval": "30s",
            "prometheusAddr": "http://r4-infrastructure-prometheus-server:80",
            "alertManagerBindAddr": ":9095"
        },
        "collector": {
            "primaryAddr": "192.168.8.229",
            "secondaryAddr": "192.168.8.229",
            "serverRoot": "",
            "primaryPort": 30417,
            "primaryUser": "sample1",
            "primaryPassword": "sample1",
            "secure": false
        }
    },
```
```shell=
vim ~/vespamgr/config/plt-counter.json
```
```json= 
[
    {
        "metadata": { },
        "descriptor": { },
        "config": {
            "local": {
                "host": ":8080"
            },
            "logger": {
                "level": 5
            },
            "measurements": [
                {
                    "moId": "SEP-12/XAPP-1",
                    "measType": "X2",
                    "measId": "9001",
                    "measInterval": "60",
                    "metrics": [
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='RICServiceUpdateFailureBytes'}",
                            "objectName": "E2TAlpha_RICServiceUpdateFailureBytes",
                            "objectInstance": "E2TAlpha_RICServiceUpdateFailureBytes",
                            "counterId": "0010",
                            "type": "counter",
                            "description": "E2TAlpha counter E2T_RICServiceUpdateFailureBytes"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='RICServiceUpdateFailureMsgs'}",
                            "objectName": "E2TAlpha_RICServiceUpdateFailureMsgs",
                            "objectInstance": "E2TAlpha_RICServiceUpdateFailureMsgs",
                            "counterId": "0011",
                            "type": "counter",
                            "description": "E2TAlpha counter RICServiceUpdateFailureMsgs"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='SetupRequestFailureBytes'}",
                            "objectName": "E2TAlpha_SetupRequestFailureBytes",
                            "objectInstance": "E2TAlpha_SetupRequestFailureBytes",
                            "counterId": "0012",
                            "type": "counter",
                            "description": "E2TAlpha counter E2T_SetupRequestFailureBytes"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='SetupRequestFailureMsgs'}",
                            "objectName": "E2TAlpha_SetupRequestFailureMsgs",
                            "objectInstance": "E2TAlpha_SetupRequestFailureMsgs",
                            "counterId": "0013",
                            "type": "counter",
                            "description": "E2TAlpha counter SetupRequestFailureMsgs"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='ResetAckBytes'}",
                            "objectName": "E2TAlpha_ResetAckBytes",
                            "objectInstance": "E2TAlpha_ResetAckBytes",
                            "counterId": "0014",
                            "type": "counter",
                            "description": "E2TAlpha counter E2T_ResetAckBytes"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='SetupResponseBytes'}",
                            "objectName": "E2TAlpha_SetupResponseBytes",
                            "objectInstance": "E2TAlpha_SetupResponseBytes",
                            "counterId": "0015",
                            "type": "counter",
                            "description": "E2TAlpha counter E2T_SetupResponseBytes"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='RICControlAckBytes'}",
                            "objectName": "E2TAlpha_RICControlAckBytes",
                            "objectInstance": "E2TAlpha_RICControlAckBytes",
                            "counterId": "0016",
                            "type": "counter",
                            "description": "E2TAlpha counter E2T_RICControlAckBytes"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='ErrorIndicationMsgs'}",
                            "objectName": "E2TAlpha_ErrorIndicationMsgs",
                            "objectInstance": "E2TAlpha_ErrorIndicationMsgs",
                            "counterId": "0017",
                            "type": "counter",
                            "description": "E2TAlpha counter ErrorIndicationMsgs"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='ResetAckMsgs'}",
                            "objectName": "E2TAlpha_ResetAckMsgs",
                            "objectInstance": "E2TAlpha_ResetAckMsgs",
                            "counterId": "0018",
                            "type": "counter",
                            "description": "E2TAlpha counter ResetAckMsgs"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='RICSubscriptionAckMsgs'}",
                            "objectName": "E2TAlpha_RICSubscriptionAckMsgs",
                            "objectInstance": "E2TAlpha_RICSubscriptionAckMsgs",
                            "counterId": "0019",
                            "type": "counter",
                            "description": "E2TAlpha counter RICSubscriptionAckMsgs"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='RICServiceUpdateMsgs'}",
                            "objectName": "E2TAlpha_RICServiceUpdateMsgs",
                            "objectInstance": "E2TAlpha_RICServiceUpdateMsgs",
                            "counterId": "0020",
                            "type": "counter",
                            "description": "E2TAlpha counter RICServiceUpdateMsgs"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='RICIndicationMsgs'}",
                            "objectName": "E2TAlpha_RICIndicationMsgs",
                            "objectInstance": "E2TAlpha_RICIndicationMsgs",
                            "counterId": "0021",
                            "type": "counter",
                            "description": "E2TAlpha counter RICIndicationMsgs"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='RICControlAckMsgs'}",
                            "objectName": "E2TAlpha_RICControlAckMsgs",
                            "objectInstance": "E2TAlpha_RICControlAckMsgs",
                            "counterId": "0022",
                            "type": "counter",
                            "description": "E2TAlpha counter RICControlAckMsgs"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='RICSubscriptionDeleteMsgs'}",
                            "objectName": "E2TAlpha_RICSubscriptionDeleteMsgs",
                            "objectInstance": "E2TAlpha_RICSubscriptionDeleteMsgs",
                            "counterId": "0023",
                            "type": "counter",
                            "description": "E2TAlpha counter RICSubscriptionDeleteMsgs"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='ResetAckBytes'}",
                            "objectName": "E2TAlpha_ResetAckBytes",
                            "objectInstance": "E2TAlpha_ResetAckBytes",
                            "counterId": "0024",
                            "type": "counter",
                            "description": "E2TAlpha counter E2T_ResetAckBytes"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='RICServiceUpdateRespMsgs'}",
                            "objectName": "E2TAlpha_RICServiceUpdateRespMsgs",
                            "objectInstance": "E2TAlpha_RICServiceUpdateRespMsgs",
                            "counterId": "0025",
                            "type": "counter",
                            "description": "E2TAlpha counter RICServiceUpdateRespMsgs"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='SetupRequestMsgs'}",
                            "objectName": "E2TAlpha_SetupRequestMsgs",
                            "objectInstance": "E2TAlpha_SetupRequestMsgs",
                            "counterId": "0026",
                            "type": "counter",
                            "description": "E2TAlpha counter SetupRequestMsgs"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='ResetAckMsgs'}",
                            "objectName": "E2TAlpha_ResetAckMsgs",
                            "objectInstance": "E2TAlpha_ResetAckMsgs",
                            "counterId": "0027",
                            "type": "counter",
                            "description": "E2TAlpha counter ResetAckMsgs"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='ResetRequestBytes'}",
                            "objectName": "E2TAlpha_ResetRequestBytes",
                            "objectInstance": "E2TAlpha_ResetRequestBytes",
                            "counterId": "0028",
                            "type": "counter",
                            "description": "E2TAlpha counter E2T_ResetRequestBytes"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='ErrorIndicationBytes'}",
                            "objectName": "E2TAlpha_ErrorIndicationBytes",
                            "objectInstance": "E2TAlpha_ErrorIndicationBytes",
                            "counterId": "0029",
                            "type": "counter",
                            "description": "E2TAlpha counter E2T_ErrorIndicationBytes"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='RICControlFailureBytes'}",
                            "objectName": "E2TAlpha_RICControlFailureBytes",
                            "objectInstance": "E2TAlpha_RICControlFailureBytes",
                            "counterId": "0030",
                            "type": "counter",
                            "description": "E2TAlpha counter E2T_RICControlFailureBytes"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='RICSubscriptionAckBytes'}",
                            "objectName": "E2TAlpha_RICSubscriptionAckBytes",
                            "objectInstance": "E2TAlpha_RICSubscriptionAckBytes",
                            "counterId": "0031",
                            "type": "counter",
                            "description": "E2TAlpha counter E2T_RICSubscriptionAckBytes"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='SetupRequestBytes'}",
                            "objectName": "E2TAlpha_SetupRequestBytes",
                            "objectInstance": "E2TAlpha_SetupRequestBytes",
                            "counterId": "0032",
                            "type": "counter",
                            "description": "E2TAlpha counter E2T_SetupRequestBytes"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='RICIndicationBytes'}",
                            "objectName": "E2TAlpha_RICIndicationBytes",
                            "objectInstance": "E2TAlpha_RICIndicationBytes",
                            "counterId": "0033",
                            "type": "counter",
                            "description": "E2TAlpha counter E2T_RICIndicationBytes"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='RICSubscriptionDeleteAckMsgs'}",
                            "objectName": "E2TAlpha_RICSubscriptionDeleteAckMsgs",
                            "objectInstance": "E2TAlpha_RICSubscriptionDeleteAckMsgs",
                            "counterId": "0034",
                            "type": "counter",
                            "description": "E2TAlpha counter RICSubscriptionDeleteAckMsgs"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='RICSubscriptionDeleteFailMsgs'}",
                            "objectName": "E2TAlpha_RICSubscriptionDeleteFailMsgs",
                            "objectInstance": "E2TAlpha_RICSubscriptionDeleteFailMsgs",
                            "counterId": "0035",
                            "type": "counter",
                            "description": "E2TAlpha counter RICSubscriptionDeleteFailMsgs"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='RICServiceQueryBytes'}",
                            "objectName": "E2TAlpha_RICServiceQueryBytes",
                            "objectInstance": "E2TAlpha_RICServiceQueryBytes",
                            "counterId": "0036",
                            "type": "counter",
                            "description": "E2TAlpha counter E2T_RICServiceQueryBytes"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='RICControlFailureMsgs'}",
                            "objectName": "E2TAlpha_RICControlFailureMsgs",
                            "objectInstance": "E2TAlpha_RICControlFailureMsgs",
                            "counterId": "0037",
                            "type": "counter",
                            "description": "E2TAlpha counter RICControlFailureMsgs"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='RICSubscriptionFailureMsgs'}",
                            "objectName": "E2TAlpha_RICSubscriptionFailureMsgs",
                            "objectInstance": "E2TAlpha_RICSubscriptionFailureMsgs",
                            "counterId": "0038",
                            "type": "counter",
                            "description": "E2TAlpha counter RICSubscriptionFailureMsgs"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='ResetRequestMsgs'}",
                            "objectName": "E2TAlpha_ResetRequestMsgs",
                            "objectInstance": "E2TAlpha_ResetRequestMsgs",
                            "counterId": "0039",
                            "type": "counter",
                            "description": "E2TAlpha counter ResetRequestMsgs"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='RICSubscriptionDeleteFailBytes'}",
                            "objectName": "E2TAlpha_RICSubscriptionDeleteFailBytes",
                            "objectInstance": "E2TAlpha_RICSubscriptionDeleteFailBytes",
                            "counterId": "0040",
                            "type": "counter",
                            "description": "E2TAlpha counter E2T_RICSubscriptionDeleteFailBytes"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='RICServiceUpdateBytes'}",
                            "objectName": "E2TAlpha_RICServiceUpdateBytes",
                            "objectInstance": "E2TAlpha_RICServiceUpdateBytes",
                            "counterId": "0041",
                            "type": "counter",
                            "description": "E2TAlpha counter E2T_RICServiceUpdateBytes"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='ErrorIndicationMsgs'}",
                            "objectName": "E2TAlpha_ErrorIndicationMsgs",
                            "objectInstance": "E2TAlpha_ErrorIndicationMsgs",
                            "counterId": "0042",
                            "type": "counter",
                            "description": "E2TAlpha counter ErrorIndicationMsgs"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='RICSubscriptionMsgs'}",
                            "objectName": "E2TAlpha_RICSubscriptionMsgs",
                            "objectInstance": "E2TAlpha_RICSubscriptionMsgs",
                            "counterId": "0043",
                            "type": "counter",
                            "description": "E2TAlpha counter RICSubscriptionMsgs"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='ErrorIndicationBytes'}",
                            "objectName": "E2TAlpha_ErrorIndicationBytes",
                            "objectInstance": "E2TAlpha_ErrorIndicationBytes",
                            "counterId": "0044",
                            "type": "counter",
                            "description": "E2TAlpha counter E2T_ErrorIndicationBytes"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='RICSubscriptionDeleteBytes'}",
                            "objectName": "E2TAlpha_RICSubscriptionDeleteBytes",
                            "objectInstance": "E2TAlpha_RICSubscriptionDeleteBytes",
                            "counterId": "0045",
                            "type": "counter",
                            "description": "E2TAlpha counter E2T_RICSubscriptionDeleteBytes"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='ResetRequestMsgs'}",
                            "objectName": "E2TAlpha_ResetRequestMsgs",
                            "objectInstance": "E2TAlpha_ResetRequestMsgs",
                            "counterId": "0046",
                            "type": "counter",
                            "description": "E2TAlpha counter ResetRequestMsgs"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='RICSubscriptionDeleteAckBytes'}",
                            "objectName": "E2TAlpha_RICSubscriptionDeleteAckBytes",
                            "objectInstance": "E2TAlpha_RICSubscriptionDeleteAckBytes",
                            "counterId": "0047",
                            "type": "counter",
                            "description": "E2TAlpha counter E2T_RICSubscriptionDeleteAckBytes"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='RICControlBytes'}",
                            "objectName": "E2TAlpha_RICControlBytes",
                            "objectInstance": "E2TAlpha_RICControlBytes",
                            "counterId": "0048",
                            "type": "counter",
                            "description": "E2TAlpha counter E2T_RICControlBytes"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='SetupResponseMsgs'}",
                            "objectName": "E2TAlpha_SetupResponseMsgs",
                            "objectInstance": "E2TAlpha_SetupResponseMsgs",
                            "counterId": "0049",
                            "type": "counter",
                            "description": "E2TAlpha counter SetupResponseMsgs"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='ResetRequestBytes'}",
                            "objectName": "E2TAlpha_ResetRequestBytes",
                            "objectInstance": "E2TAlpha_ResetRequestBytes",
                            "counterId": "0050",
                            "type": "counter",
                            "description": "E2TAlpha counter E2T_ResetRequestBytes"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='RICSubscriptionFailureBytes'}",
                            "objectName": "E2TAlpha_RICSubscriptionFailureBytes",
                            "objectInstance": "E2TAlpha_RICSubscriptionFailureBytes",
                            "counterId": "0051",
                            "type": "counter",
                            "description": "E2TAlpha counter E2T_RICSubscriptionFailureBytes"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='RICControlMsgs'}",
                            "objectName": "E2TAlpha_RICControlMsgs",
                            "objectInstance": "E2TAlpha_RICControlMsgs",
                            "counterId": "0052",
                            "type": "counter",
                            "description": "E2TAlpha counter RICControlMsgs"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='RICServiceUpdateRespBytes'}",
                            "objectName": "E2TAlpha_RICServiceUpdateRespBytes",
                            "objectInstance": "E2TAlpha_RICServiceUpdateRespBytes",
                            "counterId": "0053",
                            "type": "counter",
                            "description": "E2TAlpha counter E2T_RICServiceUpdateRespBytes"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='RICServiceQueryMsgs'}",
                            "objectName": "E2TAlpha_RICServiceQueryMsgs",
                            "objectInstance": "E2TAlpha_RICServiceQueryMsgs",
                            "counterId": "0054",
                            "type": "counter",
                            "description": "E2TAlpha counter RICServiceQueryMsgs"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='RICSubscriptionBytes'}",
                            "objectName": "E2TAlpha_RICSubscriptionBytes",
                            "objectInstance": "E2TAlpha_RICSubscriptionBytes",
                            "counterId": "0055",
                            "type": "counter",
                            "description": "E2TAlpha counter E2T_RICSubscriptionBytes"
                        }
                    ]
                }
            ]
        }
    }
]
```
**Re-build Docker Image:**
```shell=
cd ~/vespamgr
sudo docker build -t nexus3.o-ran-sc.org:10002/o-ran-sc/ric-plt-vespamgr:0.7.5 .
```

**Edit Deployment:**
```shell=
# Edit deployment for readinessProbe
kubectl edit deploy -n ricplt deployment-ricplt-vespamgr
```

```json=
spec:
  progressDeadlineSeconds: 600
  replicas: 1
  revisionHistoryLimit: 10
  selector:
    matchLabels:
      app: ricplt-vespamgr
      release: r4-vespamgr
  strategy:
    rollingUpdate:
      maxSurge: 25%
      maxUnavailable: 25%
    type: RollingUpdate
  template:
    metadata:
      creationTimestamp: null
      labels:
        app: ricplt-vespamgr
        release: r4-vespamgr
    spec:
      containers:
      - env:
        - name: VESMGR_APPMGRDOMAN
          value: service-ricplt-appmgr-http
        envFrom:
        - configMapRef:
            name: configmap-ricplt-vespamgr
        - secretRef:
            name: vespa-secrets
        image: nexus3.o-ran-sc.org:10002/o-ran-sc/ric-plt-vespamgr:0.7.5
        imagePullPolicy: IfNotPresent
        livenessProbe:
          failureThreshold: 3
          httpGet:
            path: /supervision
            port: 8080
            scheme: HTTP
          initialDelaySeconds: 30
          periodSeconds: 60
          successThreshold: 1
          timeoutSeconds: 20
        name: container-ricplt-vespamgr
        ports:
        - containerPort: 8080
          name: http
          protocol: TCP
        - containerPort: 9095
          name: alert
          protocol: TCP
        readinessProbe:
          failureThreshold: 3
          httpGet:
            path: ric/v1/health/ready
            port: 8080
            scheme: HTTP
          initialDelaySeconds: 5
          periodSeconds: 15
          successThreshold: 1
          timeoutSeconds: 1
```

![](https://hackmd.io/_uploads/BJYoYnaOn.png)

### Integrate Defined metrics of KMC xApp into VESPA Manager
```shell=
vim ~/vespamgr/config/plt-counter.json
```
:::spoiler plt-counter.json
```json=
[
    {
        "metadata": { },
        "descriptor": { },
        "config": {
            "local": {
                "host": ":8080"
            },
            "logger": {
                "level": 5
            },
            "measurements": [
                {
                    "moId": "SEP-12/XAPP-1",
                    "measType": "X2",
                    "measId": "9001",
                    "measInterval": "60",
                    "metrics": [
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='RICServiceUpdateFailureBytes'}",
                            "objectName": "E2TAlpha_RICServiceUpdateFailureBytes",
                            "objectInstance": "E2TAlpha_RICServiceUpdateFailureBytes",
                            "counterId": "0010",
                            "type": "counter",
                            "description": "E2TAlpha counter E2T_RICServiceUpdateFailureBytes"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='RICServiceUpdateFailureMsgs'}",
                            "objectName": "E2TAlpha_RICServiceUpdateFailureMsgs",
                            "objectInstance": "E2TAlpha_RICServiceUpdateFailureMsgs",
                            "counterId": "0011",
                            "type": "counter",
                            "description": "E2TAlpha counter RICServiceUpdateFailureMsgs"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='SetupRequestFailureBytes'}",
                            "objectName": "E2TAlpha_SetupRequestFailureBytes",
                            "objectInstance": "E2TAlpha_SetupRequestFailureBytes",
                            "counterId": "0012",
                            "type": "counter",
                            "description": "E2TAlpha counter E2T_SetupRequestFailureBytes"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='SetupRequestFailureMsgs'}",
                            "objectName": "E2TAlpha_SetupRequestFailureMsgs",
                            "objectInstance": "E2TAlpha_SetupRequestFailureMsgs",
                            "counterId": "0013",
                            "type": "counter",
                            "description": "E2TAlpha counter SetupRequestFailureMsgs"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='ResetAckBytes'}",
                            "objectName": "E2TAlpha_ResetAckBytes",
                            "objectInstance": "E2TAlpha_ResetAckBytes",
                            "counterId": "0014",
                            "type": "counter",
                            "description": "E2TAlpha counter E2T_ResetAckBytes"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='SetupResponseBytes'}",
                            "objectName": "E2TAlpha_SetupResponseBytes",
                            "objectInstance": "E2TAlpha_SetupResponseBytes",
                            "counterId": "0015",
                            "type": "counter",
                            "description": "E2TAlpha counter E2T_SetupResponseBytes"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='RICControlAckBytes'}",
                            "objectName": "E2TAlpha_RICControlAckBytes",
                            "objectInstance": "E2TAlpha_RICControlAckBytes",
                            "counterId": "0016",
                            "type": "counter",
                            "description": "E2TAlpha counter E2T_RICControlAckBytes"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='ErrorIndicationMsgs'}",
                            "objectName": "E2TAlpha_ErrorIndicationMsgs",
                            "objectInstance": "E2TAlpha_ErrorIndicationMsgs",
                            "counterId": "0017",
                            "type": "counter",
                            "description": "E2TAlpha counter ErrorIndicationMsgs"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='ResetAckMsgs'}",
                            "objectName": "E2TAlpha_ResetAckMsgs",
                            "objectInstance": "E2TAlpha_ResetAckMsgs",
                            "counterId": "0018",
                            "type": "counter",
                            "description": "E2TAlpha counter ResetAckMsgs"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='RICSubscriptionAckMsgs'}",
                            "objectName": "E2TAlpha_RICSubscriptionAckMsgs",
                            "objectInstance": "E2TAlpha_RICSubscriptionAckMsgs",
                            "counterId": "0019",
                            "type": "counter",
                            "description": "E2TAlpha counter RICSubscriptionAckMsgs"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='RICServiceUpdateMsgs'}",
                            "objectName": "E2TAlpha_RICServiceUpdateMsgs",
                            "objectInstance": "E2TAlpha_RICServiceUpdateMsgs",
                            "counterId": "0020",
                            "type": "counter",
                            "description": "E2TAlpha counter RICServiceUpdateMsgs"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='RICIndicationMsgs'}",
                            "objectName": "E2TAlpha_RICIndicationMsgs",
                            "objectInstance": "E2TAlpha_RICIndicationMsgs",
                            "counterId": "0021",
                            "type": "counter",
                            "description": "E2TAlpha counter RICIndicationMsgs"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='RICControlAckMsgs'}",
                            "objectName": "E2TAlpha_RICControlAckMsgs",
                            "objectInstance": "E2TAlpha_RICControlAckMsgs",
                            "counterId": "0022",
                            "type": "counter",
                            "description": "E2TAlpha counter RICControlAckMsgs"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='RICSubscriptionDeleteMsgs'}",
                            "objectName": "E2TAlpha_RICSubscriptionDeleteMsgs",
                            "objectInstance": "E2TAlpha_RICSubscriptionDeleteMsgs",
                            "counterId": "0023",
                            "type": "counter",
                            "description": "E2TAlpha counter RICSubscriptionDeleteMsgs"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='ResetAckBytes'}",
                            "objectName": "E2TAlpha_ResetAckBytes",
                            "objectInstance": "E2TAlpha_ResetAckBytes",
                            "counterId": "0024",
                            "type": "counter",
                            "description": "E2TAlpha counter E2T_ResetAckBytes"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='RICServiceUpdateRespMsgs'}",
                            "objectName": "E2TAlpha_RICServiceUpdateRespMsgs",
                            "objectInstance": "E2TAlpha_RICServiceUpdateRespMsgs",
                            "counterId": "0025",
                            "type": "counter",
                            "description": "E2TAlpha counter RICServiceUpdateRespMsgs"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='SetupRequestMsgs'}",
                            "objectName": "E2TAlpha_SetupRequestMsgs",
                            "objectInstance": "E2TAlpha_SetupRequestMsgs",
                            "counterId": "0026",
                            "type": "counter",
                            "description": "E2TAlpha counter SetupRequestMsgs"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='ResetAckMsgs'}",
                            "objectName": "E2TAlpha_ResetAckMsgs",
                            "objectInstance": "E2TAlpha_ResetAckMsgs",
                            "counterId": "0027",
                            "type": "counter",
                            "description": "E2TAlpha counter ResetAckMsgs"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='ResetRequestBytes'}",
                            "objectName": "E2TAlpha_ResetRequestBytes",
                            "objectInstance": "E2TAlpha_ResetRequestBytes",
                            "counterId": "0028",
                            "type": "counter",
                            "description": "E2TAlpha counter E2T_ResetRequestBytes"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='ErrorIndicationBytes'}",
                            "objectName": "E2TAlpha_ErrorIndicationBytes",
                            "objectInstance": "E2TAlpha_ErrorIndicationBytes",
                            "counterId": "0029",
                            "type": "counter",
                            "description": "E2TAlpha counter E2T_ErrorIndicationBytes"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='RICControlFailureBytes'}",
                            "objectName": "E2TAlpha_RICControlFailureBytes",
                            "objectInstance": "E2TAlpha_RICControlFailureBytes",
                            "counterId": "0030",
                            "type": "counter",
                            "description": "E2TAlpha counter E2T_RICControlFailureBytes"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='RICSubscriptionAckBytes'}",
                            "objectName": "E2TAlpha_RICSubscriptionAckBytes",
                            "objectInstance": "E2TAlpha_RICSubscriptionAckBytes",
                            "counterId": "0031",
                            "type": "counter",
                            "description": "E2TAlpha counter E2T_RICSubscriptionAckBytes"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='SetupRequestBytes'}",
                            "objectName": "E2TAlpha_SetupRequestBytes",
                            "objectInstance": "E2TAlpha_SetupRequestBytes",
                            "counterId": "0032",
                            "type": "counter",
                            "description": "E2TAlpha counter E2T_SetupRequestBytes"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='RICIndicationBytes'}",
                            "objectName": "E2TAlpha_RICIndicationBytes",
                            "objectInstance": "E2TAlpha_RICIndicationBytes",
                            "counterId": "0033",
                            "type": "counter",
                            "description": "E2TAlpha counter E2T_RICIndicationBytes"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='RICSubscriptionDeleteAckMsgs'}",
                            "objectName": "E2TAlpha_RICSubscriptionDeleteAckMsgs",
                            "objectInstance": "E2TAlpha_RICSubscriptionDeleteAckMsgs",
                            "counterId": "0034",
                            "type": "counter",
                            "description": "E2TAlpha counter RICSubscriptionDeleteAckMsgs"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='RICSubscriptionDeleteFailMsgs'}",
                            "objectName": "E2TAlpha_RICSubscriptionDeleteFailMsgs",
                            "objectInstance": "E2TAlpha_RICSubscriptionDeleteFailMsgs",
                            "counterId": "0035",
                            "type": "counter",
                            "description": "E2TAlpha counter RICSubscriptionDeleteFailMsgs"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='RICServiceQueryBytes'}",
                            "objectName": "E2TAlpha_RICServiceQueryBytes",
                            "objectInstance": "E2TAlpha_RICServiceQueryBytes",
                            "counterId": "0036",
                            "type": "counter",
                            "description": "E2TAlpha counter E2T_RICServiceQueryBytes"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='RICControlFailureMsgs'}",
                            "objectName": "E2TAlpha_RICControlFailureMsgs",
                            "objectInstance": "E2TAlpha_RICControlFailureMsgs",
                            "counterId": "0037",
                            "type": "counter",
                            "description": "E2TAlpha counter RICControlFailureMsgs"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='RICSubscriptionFailureMsgs'}",
                            "objectName": "E2TAlpha_RICSubscriptionFailureMsgs",
                            "objectInstance": "E2TAlpha_RICSubscriptionFailureMsgs",
                            "counterId": "0038",
                            "type": "counter",
                            "description": "E2TAlpha counter RICSubscriptionFailureMsgs"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='ResetRequestMsgs'}",
                            "objectName": "E2TAlpha_ResetRequestMsgs",
                            "objectInstance": "E2TAlpha_ResetRequestMsgs",
                            "counterId": "0039",
                            "type": "counter",
                            "description": "E2TAlpha counter ResetRequestMsgs"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='RICSubscriptionDeleteFailBytes'}",
                            "objectName": "E2TAlpha_RICSubscriptionDeleteFailBytes",
                            "objectInstance": "E2TAlpha_RICSubscriptionDeleteFailBytes",
                            "counterId": "0040",
                            "type": "counter",
                            "description": "E2TAlpha counter E2T_RICSubscriptionDeleteFailBytes"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='RICServiceUpdateBytes'}",
                            "objectName": "E2TAlpha_RICServiceUpdateBytes",
                            "objectInstance": "E2TAlpha_RICServiceUpdateBytes",
                            "counterId": "0041",
                            "type": "counter",
                            "description": "E2TAlpha counter E2T_RICServiceUpdateBytes"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='ErrorIndicationMsgs'}",
                            "objectName": "E2TAlpha_ErrorIndicationMsgs",
                            "objectInstance": "E2TAlpha_ErrorIndicationMsgs",
                            "counterId": "0042",
                            "type": "counter",
                            "description": "E2TAlpha counter ErrorIndicationMsgs"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='RICSubscriptionMsgs'}",
                            "objectName": "E2TAlpha_RICSubscriptionMsgs",
                            "objectInstance": "E2TAlpha_RICSubscriptionMsgs",
                            "counterId": "0043",
                            "type": "counter",
                            "description": "E2TAlpha counter RICSubscriptionMsgs"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='ErrorIndicationBytes'}",
                            "objectName": "E2TAlpha_ErrorIndicationBytes",
                            "objectInstance": "E2TAlpha_ErrorIndicationBytes",
                            "counterId": "0044",
                            "type": "counter",
                            "description": "E2TAlpha counter E2T_ErrorIndicationBytes"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='RICSubscriptionDeleteBytes'}",
                            "objectName": "E2TAlpha_RICSubscriptionDeleteBytes",
                            "objectInstance": "E2TAlpha_RICSubscriptionDeleteBytes",
                            "counterId": "0045",
                            "type": "counter",
                            "description": "E2TAlpha counter E2T_RICSubscriptionDeleteBytes"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='ResetRequestMsgs'}",
                            "objectName": "E2TAlpha_ResetRequestMsgs",
                            "objectInstance": "E2TAlpha_ResetRequestMsgs",
                            "counterId": "0046",
                            "type": "counter",
                            "description": "E2TAlpha counter ResetRequestMsgs"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='RICSubscriptionDeleteAckBytes'}",
                            "objectName": "E2TAlpha_RICSubscriptionDeleteAckBytes",
                            "objectInstance": "E2TAlpha_RICSubscriptionDeleteAckBytes",
                            "counterId": "0047",
                            "type": "counter",
                            "description": "E2TAlpha counter E2T_RICSubscriptionDeleteAckBytes"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='RICControlBytes'}",
                            "objectName": "E2TAlpha_RICControlBytes",
                            "objectInstance": "E2TAlpha_RICControlBytes",
                            "counterId": "0048",
                            "type": "counter",
                            "description": "E2TAlpha counter E2T_RICControlBytes"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='SetupResponseMsgs'}",
                            "objectName": "E2TAlpha_SetupResponseMsgs",
                            "objectInstance": "E2TAlpha_SetupResponseMsgs",
                            "counterId": "0049",
                            "type": "counter",
                            "description": "E2TAlpha counter SetupResponseMsgs"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='ResetRequestBytes'}",
                            "objectName": "E2TAlpha_ResetRequestBytes",
                            "objectInstance": "E2TAlpha_ResetRequestBytes",
                            "counterId": "0050",
                            "type": "counter",
                            "description": "E2TAlpha counter E2T_ResetRequestBytes"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='RICSubscriptionFailureBytes'}",
                            "objectName": "E2TAlpha_RICSubscriptionFailureBytes",
                            "objectInstance": "E2TAlpha_RICSubscriptionFailureBytes",
                            "counterId": "0051",
                            "type": "counter",
                            "description": "E2TAlpha counter E2T_RICSubscriptionFailureBytes"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='RICControlMsgs'}",
                            "objectName": "E2TAlpha_RICControlMsgs",
                            "objectInstance": "E2TAlpha_RICControlMsgs",
                            "counterId": "0052",
                            "type": "counter",
                            "description": "E2TAlpha counter RICControlMsgs"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='RICServiceUpdateRespBytes'}",
                            "objectName": "E2TAlpha_RICServiceUpdateRespBytes",
                            "objectInstance": "E2TAlpha_RICServiceUpdateRespBytes",
                            "counterId": "0053",
                            "type": "counter",
                            "description": "E2TAlpha counter E2T_RICServiceUpdateRespBytes"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='RICServiceQueryMsgs'}",
                            "objectName": "E2TAlpha_RICServiceQueryMsgs",
                            "objectInstance": "E2TAlpha_RICServiceQueryMsgs",
                            "counterId": "0054",
                            "type": "counter",
                            "description": "E2TAlpha counter RICServiceQueryMsgs"
                        },
                        {
                            "name": "E2TAlpha{POD_NAME='e2term',counter='RICSubscriptionBytes'}",
                            "objectName": "E2TAlpha_RICSubscriptionBytes",
                            "objectInstance": "E2TAlpha_RICSubscriptionBytes",
                            "counterId": "0055",
                            "type": "counter",
                            "description": "E2TAlpha counter E2T_RICSubscriptionBytes"
                        }
                    ]
                },
                {
                    "moId": "SEP-12/XAPP-2",
                    "measType": "X2",
                    "measId": "9002",
                    "measInterval": "60",
                    "metrics": [
                        {
                            "name": "(sum by (pod_name, container_namespace, instance) ( irate(kepler_container_joules_total{pod_name=~'.*a1mediator.*'}[1m])) )",
                            "objectName": "kepler_power_a1mediator",
                            "objectInstance": "kepler_power_a1mediator",
                            "counterId": "0110",
                            "type": "counter",
                            "description": "kepler_power of a1mediator"
                        },
                        {
                            "name": "(sum by (pod_name, container_namespace, instance) ( irate(kepler_container_joules_total{pod_name=~'.*alarmmanager.*'}[1m])) )",
                            "objectName": "kepler_power_alarmmanager",
                            "objectInstance": "kepler_power_alarmmanager",
                            "counterId": "0111",
                            "type": "counter",
                            "description": "kepler_power of alarmmanager"
                        },
                        {
                            "name": "(sum by (pod_name, container_namespace, instance) ( irate(kepler_container_joules_total{pod_name=~'.*appmgr.*'}[1m])) )",
                            "objectName": "kepler_power_appmgr",
                            "objectInstance": "kepler_power_appmgr",
                            "counterId": "0112",
                            "type": "counter",
                            "description": "kepler_power of appmgr"
                        },
                        {
                            "name": "(sum by (pod_name, container_namespace, instance) ( irate(kepler_container_joules_total{pod_name=~'.*e2mgr.*'}[1m])) )",
                            "objectName": "kepler_power_e2mgr",
                            "objectInstance": "kepler_power_e2mgr",
                            "counterId": "0113",
                            "type": "counter",
                            "description": "kepler_power of e2mgr"
                        },
                        {
                            "name": "(sum by (pod_name, container_namespace, instance) ( irate(kepler_container_joules_total{pod_name=~'.*e2term.*'}[1m])) )",
                            "objectName": "kepler_power_e2term",
                            "objectInstance": "kepler_power_e2term",
                            "counterId": "0114",
                            "type": "counter",
                            "description": "kepler_power of e2term"
                        },
                        {
                            "name": "(sum by (pod_name, container_namespace, instance) ( irate(kepler_container_joules_total{pod_name=~'.*jaegeradapter.*'}[1m])) )",
                            "objectName": "kepler_power_jaegeradapter",
                            "objectInstance": "kepler_power_jaegeradapter",
                            "counterId": "0115",
                            "type": "counter",
                            "description": "kepler_power of jaegeradapter"
                        },
                        {
                            "name": "(sum by (pod_name, container_namespace, instance) ( irate(kepler_container_joules_total{pod_name=~'.*o1mediator.*'}[1m])) )",
                            "objectName": "kepler_power_o1mediator",
                            "objectInstance": "kepler_power_o1mediator",
                            "counterId": "0116",
                            "type": "counter",
                            "description": "kepler_power of o1mediator"
                        },
                        {
                            "name": "(sum by (pod_name, container_namespace, instance) ( irate(kepler_container_joules_total{pod_name=~'.*rtmgr.*'}[1m])) )",
                            "objectName": "kepler_power_rtmgr",
                            "objectInstance": "kepler_power_rtmgr",
                            "counterId": "0117",
                            "type": "counter",
                            "description": "kepler_power of rtmgr"
                        },
                        {
                            "name": "(sum by (pod_name, container_namespace, instance) ( irate(kepler_container_joules_total{pod_name=~'.*submgr.*'}[1m])) )",
                            "objectName": "kepler_power_submgr",
                            "objectInstance": "kepler_power_submgr",
                            "counterId": "0120",
                            "type": "counter",
                            "description": "kepler_power of submgr"
                        },
                        {
                            "name": "(sum by (pod_name, container_namespace, instance) ( irate(kepler_container_joules_total{pod_name=~'.*vespamgr.*'}[1m])) )",
                            "objectName": "kepler_power_vespamgr",
                            "objectInstance": "kepler_power_vespamgr",
                            "counterId": "0121",
                            "type": "counter",
                            "description": "kepler_power of vespamgr"
                        },
                        {
                            "name": "(sum by (pod_name, container_namespace, instance) ( irate(kepler_container_joules_total{pod_name=~'.*influxdb.*'}[1m])) )",
                            "objectName": "kepler_power_influxdb2",
                            "objectInstance": "kepler_power_influxdb2",
                            "counterId": "0122",
                            "type": "counter",
                            "description": "kepler_power of influxdb2"
                        },
                        {
                            "name": "(sum by (pod_name, container_namespace, instance) ( irate(kepler_container_joules_total{pod_name=~'.*prometheus-alertmanager.*'}[1m])) )",
                            "objectName": "kepler_power_alertmanager",
                            "objectInstance": "kepler_power_alertmanager",
                            "counterId": "0123",
                            "type": "counter",
                            "description": "kepler_power of alertmanager"
                        },
                        {
                            "name": "(sum by (pod_name, container_namespace, instance) ( irate(kepler_container_joules_total{pod_name=~'.*prometheus-server.*'}[1m])) )",
                            "objectName": "kepler_power_prometheus",
                            "objectInstance": "kepler_power_prometheus",
                            "counterId": "0124",
                            "type": "counter",
                            "description": "kepler_power of prometheus"
                        },
                        {
                            "name": "(sum by (pod_name, container_namespace, instance) ( irate(kepler_container_joules_total{pod_name=~'.*dbaas.*'}[1m])) )",
                            "objectName": "kepler_power_dbaas",
                            "objectInstance": "kepler_power_dbaas",
                            "counterId": "0125",
                            "type": "counter",
                            "description": "kepler_power of dbaas"
                        },
                        {
                            "name": "sum(rate(container_cpu_usage_seconds_total{pod=~'.*a1mediator.*'}[5m])*100) by (pod, namespace,instance)",
                            "objectName": "CPU_Utilization_a1mediator",
                            "objectInstance": "CPU_Utilization_a1mediator",
                            "counterId": "0210",
                            "type": "counter",
                            "description": "CPU_Utilization of a1mediator"
                        },
                        {
                            "name": "sum(rate(container_cpu_usage_seconds_total{pod=~'.*alarmmanager.*'}[5m])*100) by (pod, namespace,instance)",
                            "objectName": "CPU_Utilization_alarmmanager",
                            "objectInstance": "CPU_Utilization_alarmmanager",
                            "counterId": "0211",
                            "type": "counter",
                            "description": "CPU_Utilization of alarmmanager"
                        },
                        {
                            "name": "sum(rate(container_cpu_usage_seconds_total{pod=~'.*appmgr.*'}[5m])*100) by (pod, namespace,instance)",
                            "objectName": "CPU_Utilization_appmgr",
                            "objectInstance": "CPU_Utilization_appmgr",
                            "counterId": "0212",
                            "type": "counter",
                            "description": "CPU_Utilization of appmgr"
                        },
                        {
                            "name": "sum(rate(container_cpu_usage_seconds_total{pod=~'.*e2mgr.*'}[5m])*100) by (pod, namespace,instance)",
                            "objectName": "CPU_Utilization_e2mgr",
                            "objectInstance": "CPU_Utilization_e2mgr",
                            "counterId": "0213",
                            "type": "counter",
                            "description": "CPU_Utilization of e2mgr"
                        },
                        {
                            "name": "sum(rate(container_cpu_usage_seconds_total{pod=~'.*e2term.*'}[5m])*100) by (pod, namespace,instance)",
                            "objectName": "CPU_Utilization_e2term",
                            "objectInstance": "CPU_Utilization_e2term",
                            "counterId": "0214",
                            "type": "counter",
                            "description": "CPU_Utilization of e2term"
                        },
                        {
                            "name": "sum(rate(container_cpu_usage_seconds_total{pod=~'.*jaegeradapter.*'}[5m])*100) by (pod, namespace,instance)",
                            "objectName": "CPU_Utilization_jaegeradapter",
                            "objectInstance": "CPU_Utilization_jaegeradapter",
                            "counterId": "0215",
                            "type": "counter",
                            "description": "CPU_Utilization of jaegeradapter"
                        },
                        {
                            "name": "sum(rate(container_cpu_usage_seconds_total{pod=~'.*o1mediator.*'}[5m])*100) by (pod, namespace,instance)",
                            "objectName": "CPU_Utilization_o1mediator",
                            "objectInstance": "CPU_Utilization_o1mediator",
                            "counterId": "0216",
                            "type": "counter",
                            "description": "CPU_Utilization of o1mediator"
                        },
                        {
                            "name": "sum(rate(container_cpu_usage_seconds_total{pod=~'.*rtmgr.*'}[5m])*100) by (pod, namespace,instance)",
                            "objectName": "CPU_Utilization_rtmgr",
                            "objectInstance": "CPU_Utilization_rtmgr",
                            "counterId": "0217",
                            "type": "counter",
                            "description": "CPU_Utilization of rtmgr"
                        },
                        {
                            "name": "sum(rate(container_cpu_usage_seconds_total{pod=~'.*submgr.*'}[5m])*100) by (pod, namespace,instance)",
                            "objectName": "CPU_Utilization_submgr",
                            "objectInstance": "CPU_Utilization_submgr",
                            "counterId": "0220",
                            "type": "counter",
                            "description": "CPU_Utilization of submgr"
                        },
                        {
                            "name": "sum(rate(container_cpu_usage_seconds_total{pod=~'.*vespamgr.*'}[5m])*100) by (pod, namespace,instance)",
                            "objectName": "CPU_Utilization_vespamgr",
                            "objectInstance": "CPU_Utilization_vespamgr",
                            "counterId": "0221",
                            "type": "counter",
                            "description": "CPU_Utilization of vespamgr"
                        },
                        {
                            "name": "sum(rate(container_cpu_usage_seconds_total{pod=~'.*influxdb.*'}[5m])*100) by (pod, namespace,instance)",
                            "objectName": "CPU_Utilization_influxdb2",
                            "objectInstance": "CPU_Utilization_influxdb2",
                            "counterId": "0222",
                            "type": "counter",
                            "description": "CPU_Utilization of influxdb2"
                        },
                        {
                            "name": "sum(rate(container_cpu_usage_seconds_total{pod=~'.*prometheus-alertmanager.*'}[5m])*100) by (pod, namespace,instance)",
                            "objectName": "CPU_Utilization_alertmanager",
                            "objectInstance": "CPU_Utilization_alertmanager",
                            "counterId": "0223",
                            "type": "counter",
                            "description": "CPU_Utilization of alertmanager"
                        },
                        {
                            "name": "sum(rate(container_cpu_usage_seconds_total{pod=~'.*prometheus-server.*'}[5m])*100) by (pod, namespace,instance)",
                            "objectName": "CPU_Utilization_prometheus",
                            "objectInstance": "CPU_Utilization_prometheus",
                            "counterId": "0224",
                            "type": "counter",
                            "description": "CPU_Utilization of prometheus"
                        },
                        {
                            "name": "sum(rate(container_cpu_usage_seconds_total{pod=~'.*dbaas.*'}[5m])*100) by (pod, namespace,instance)",
                            "objectName": "CPU_Utilization_dbaas",
                            "objectInstance": "CPU_Utilization_dbaas",
                            "counterId": "0225",
                            "type": "counter",
                            "description": "CPU_Utilization of dbaas"
                        },
                        {
                            "name": "sum(container_memory_working_set_bytes{name!~'.*POD.*', pod=~'.*a1mediator.*'}) by (pod, namespace, instance) /1024/1024",
                            "objectName": "MEM_Utilization_a1mediator",
                            "objectInstance": "MEM_Utilization_a1mediator",
                            "counterId": "0310",
                            "type": "counter",
                            "description": "MEM_Utilization of a1mediator"
                        },
                        {
                            "name": "sum(container_memory_working_set_bytes{name!~'.*POD.*', pod=~'.*alarmmanager.*'}) by (pod, namespace, instance) /1024/1024",
                            "objectName": "MEM_Utilization_alarmmanager",
                            "objectInstance": "MEM_Utilization_alarmmanager",
                            "counterId": "0311",
                            "type": "counter",
                            "description": "MEM_Utilization of alarmmanager"
                        },
                        {
                            "name": "sum(container_memory_working_set_bytes{name!~'.*POD.*', pod=~'.*appmgr.*'}) by (pod, namespace, instance) /1024/1024",
                            "objectName": "MEM_Utilization_appmgr",
                            "objectInstance": "MEM_Utilization_appmgr",
                            "counterId": "0312",
                            "type": "counter",
                            "description": "MEM_Utilization of appmgr"
                        },
                        {
                            "name": "sum(container_memory_working_set_bytes{name!~'.*POD.*', pod=~'.*e2mgr.*'}) by (pod, namespace, instance) /1024/1024",
                            "objectName": "MEM_Utilization_e2mgr",
                            "objectInstance": "MEM_Utilization_e2mgr",
                            "counterId": "0313",
                            "type": "counter",
                            "description": "MEM_Utilization of e2mgr"
                        },
                        {
                            "name": "sum(container_memory_working_set_bytes{name!~'.*POD.*', pod=~'.*e2term.*'}) by (pod, namespace, instance) /1024/1024",
                            "objectName": "MEM_Utilization_e2term",
                            "objectInstance": "MEM_Utilization_e2term",
                            "counterId": "0314",
                            "type": "counter",
                            "description": "MEM_Utilization of e2term"
                        },
                        {
                            "name": "sum(container_memory_working_set_bytes{name!~'.*POD.*', pod=~'.*jaegeradapter.*'}) by (pod, namespace, instance) /1024/1024",
                            "objectName": "MEM_Utilization_jaegeradapter",
                            "objectInstance": "MEM_Utilization_jaegeradapter",
                            "counterId": "0315",
                            "type": "counter",
                            "description": "MEM_Utilization of jaegeradapter"
                        },
                        {
                            "name": "sum(container_memory_working_set_bytes{name!~'.*POD.*', pod=~'.*o1mediator.*'}) by (pod, namespace, instance) /1024/1024",
                            "objectName": "MEM_Utilization_o1mediator",
                            "objectInstance": "MEM_Utilization_o1mediator",
                            "counterId": "0316",
                            "type": "counter",
                            "description": "MEM_Utilization of o1mediator"
                        },
                        {
                            "name": "sum(container_memory_working_set_bytes{name!~'.*POD.*', pod=~'.*rtmgr.*'}) by (pod, namespace, instance) /1024/1024",
                            "objectName": "MEM_Utilization_rtmgr",
                            "objectInstance": "MEM_Utilization_rtmgr",
                            "counterId": "0317",
                            "type": "counter",
                            "description": "MEM_Utilization of rtmgr"
                        },
                        {
                            "name": "sum(container_memory_working_set_bytes{name!~'.*POD.*', pod=~'.*submgr.*'}) by (pod, namespace, instance) /1024/1024",
                            "objectName": "MEM_Utilization_submgr",
                            "objectInstance": "MEM_Utilization_submgr",
                            "counterId": "0320",
                            "type": "counter",
                            "description": "MEM_Utilization of submgr"
                        },
                        {
                            "name": "sum(container_memory_working_set_bytes{name!~'.*POD.*', pod=~'.*vespamgr.*'}) by (pod, namespace, instance) /1024/1024",
                            "objectName": "MEM_Utilization_vespamgr",
                            "objectInstance": "MEM_Utilization_vespamgr",
                            "counterId": "0321",
                            "type": "counter",
                            "description": "MEM_Utilization of vespamgr"
                        },
                        {
                            "name": "sum(container_memory_working_set_bytes{name!~'.*POD.*', pod=~'.*influxdb.*'}) by (pod, namespace, instance) /1024/1024",
                            "objectName": "MEM_Utilization_influxdb2",
                            "objectInstance": "MEM_Utilization_influxdb2",
                            "counterId": "0322",
                            "type": "counter",
                            "description": "MEM_Utilization of influxdb2"
                        },
                        {
                            "name": "sum(container_memory_working_set_bytes{name!~'.*POD.*', pod=~'.*prometheus-alertmanager.*'}) by (pod, namespace, instance) /1024/1024",
                            "objectName": "MEM_Utilization_alertmanager",
                            "objectInstance": "MEM_Utilization_alertmanager",
                            "counterId": "0323",
                            "type": "counter",
                            "description": "MEM_Utilization of alertmanager"
                        },
                        {
                            "name": "sum(container_memory_working_set_bytes{name!~'.*POD.*', pod=~'.*prometheus-server.*'}) by (pod, namespace, instance) /1024/1024",
                            "objectName": "MEM_Utilization_prometheus",
                            "objectInstance": "MEM_Utilization_prometheus",
                            "counterId": "0324",
                            "type": "counter",
                            "description": "MEM_Utilization of prometheus"
                        },
                        {
                            "name": "sum(container_memory_working_set_bytes{name!~'.*POD.*', pod=~'.*dbaas.*'}) by (pod, namespace, instance) /1024/1024",
                            "objectName": "MEM_Utilization_dbaas",
                            "objectInstance": "MEM_Utilization_dbaas",
                            "counterId": "0325",
                            "type": "counter",
                            "description": "MEM_Utilization of dbaas"
                        }
                    ]
                }
            ]
        }
    }
]
```
:::

### 2-2 SMO: VES Collector
**Edit configuration of VES Collector:**
```shell=
# Edit the configuration
kubectl edit configmap -n onap onap-dcae-ves-collector-application-config-configmap
```
* auth.method: `certBasicAuth` -> `noAuth`
* collector.service.port: `8080` -> `8443`

**Restart the VES Collector:**
```shell=
# Find the pod
kubectl get pod -n onap | grep ves

# Delete the pod, it will restart one automatically
kubectl delete pod -n onap <name_of_vescollector_pod>
```

## 3. Integration
:::info
* URL: https://192.168.8.229:30205/odlux/index.html#/login
* Username: `admin`
* Password: `Kp8bJ4SXszM0WXlhak3eHlcse2gAw84vaoGGmJvUy2U`
:::

### 3-1 Log
**VESPA Manager Log**
![](https://hackmd.io/_uploads/BJtaWBWKh.png)

**VES Collector Log**
![](https://hackmd.io/_uploads/r1qzvqtKh.png)

