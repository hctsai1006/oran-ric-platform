---
tags: 【RIC-platform note】
---
# [G Release] Improve Near-RT RIC Platform
:::success
**Intro:**

We can edit config before deploying the RIC Platform that we don’t need to integrate platform again.(It can save time, but it is difficult…)

**Aims:**

- [x] Edit config before deploy the RIC Platform

**Main Reference:**
[[F Release] Improve Near-RT RIC Platform](https://hackmd.io/@Min-xiang/S1o407hqc#13-Log-Level-Configuration)
:::

## 1. Introduction
### Why to do this ?
Consider a scenario, we need to deploy the platform several times and configure the configuration every times, which needs a lot of time to do. Thus, if we can adjust the setting before deploying the platform, we can save a lot of time.

### Something to do
- Log-Level Configuration
- routing path(MType)
- Connection(URL)
- Configuration(PLMN…)

### Log-Level Configuration
In G Release, I adjust the log-level for a1mediator, appmgr and e2term.

|  Component   |    Default     | Adjust? |        How to Configure?        | Finish? |
|:------------:|:--------------:|:-------:|:-------------------------------:|:-------:|
|  a1mediator  |      none      |   Yes   |               CM                |    o    |
| alarmmanager | level 4(Debug) |    N    |               CM                |         |
|    appmgr    |      none      |   Yes   |               CM                |    o    |
|    e2mgr     | level 3(Info)  |    N    |               CM                |         |
|    e2term    | level 1(error) |   Yes   |               CM                |    o    |
|  o1mediator  | level 4(Debug) |    N    |               CM                |         |
|    rtmgr     | level 4(Debug) |    N    |               CM                |         |
|    submgr    | level 3(Info)  |    N    |            Hard code            |         |
|   vespamgr   | level 4(Debug) |    N    | /etc/ves-agent/ves-agent.yaml ? |         |

## 2. Modify the code of xApp Manager
### 2.1 Modify the Log-Level
```javascript=
vim ~/ric-dep/helm/appmgr/resources/appmgr.yaml
```
**Add loglevel “DEBUG”：**
```javascript=
"xapp":
  #Namespace to install xAPPs
  "namespace": __XAPP_NAMESPACE__
  "tarDir": "/tmp"
  "schema": "descriptors/schema.json"
  "config": "config/config-file.json"
  "tmpConfig": "/tmp/config-file.json"
"loglevel" :  4
```
- add `"loglevel" :  4`
![](https://i.imgur.com/mm8EDlX.png)

## 3. Modify the code of A1 Mediator
### 3.1 Modify the Log-Level
**Step 1：Modify the loglevel.txt section**
```javascript=
vim ~/ric-dep/helm/a1mediator/templates/config.yaml
```
```javascript=
...
    rte|20011|{{ include "common.servicename.a1mediator.rmr" . }}.{{ include "common.namespace.platform" . }}:{{ include "common.serviceport.a1mediator.rmr.data" . }}
    rte|20012|{{ include "common.servicename.a1mediator.rmr" . }}.{{ include "common.namespace.platform" . }}:{{ include "common.serviceport.a1mediator.rmr.data" . }}
    newrt|end
  loglevel.txt: |
    log-level: {{ .Values.a1mediator.loglevel }}
```
- change `log-level: {{ .Values.loglevel }}` to `log-level: {{ .Values.a1mediator.loglevel }}`
![](https://i.imgur.com/8QnrxYT.png)
**Step 2：Change loglevel from INFO to DEBUG & change Component Connection**
```javascript=
vim ~/ric-dep/helm/a1mediator/values.yaml
```
```javascript=
# these are ENV variables that A1 takes; see docs
  rmr_timeout_config:
    a1_rcv_retry_times: 20
    ins_del_no_resp_ttl: 5
    ins_del_resp_ttl: 10
  loglevel: "DEBUG"
  a1ei:
    ecs_ip_port: "http://<ecs_host>:<ecs_port>"
```
- Change loglevel from INFO to DEBUG & add `a1ei:
    ecs_ip_port: "http://<ecs_host>:<ecs_port>`
![](https://i.imgur.com/oCKGvWh.png)

### 3.2 Component Connection
**Step 1：Add ENV for A1EI**
```javascript=
vim ~/ric-dep/helm/a1mediator/templates/env.yaml
```
```javascript=
data:
  ...
  ...
  ECS_SERVICE_HOST: {{ .Values.a1mediator.a1ei.ecs_ip_port }}
```
- add `ECS_SERVICE_HOST: {{ .Values.a1mediator.a1ei.ecs_ip_port }}`
![](https://i.imgur.com/G99wnhV.png)

## 4 Modify the code of E2 Termination
### 4.1 Modify the Log-Level
**Step 1：Change loglevel from ERR to 4 (Debug)**
```javascript=
vim ~/ric-dep/helm/e2term/values.yaml
```
```javascript=
health:
    liveness:
      command: "ip=`hostname -i`;export RMR_SRC_ID=$ip;/opt/e2/rmr_probe -h $ip"
      initialDelaySeconds: 10
      periodSeconds: 10
      enabled: true

    readiness:
      command: "ip=`hostname -i`;export RMR_SRC_ID=$ip;/opt/e2/rmr_probe -h $ip"
      initialDelaySeconds: 120
      periodSeconds: 60
      enabled: true

loglevel: 4

common_env_variables:
  ConfigMapName: "/etc/config/log-level"
  ServiceName: "RIC_E2_TERM"
```
![](https://i.imgur.com/7xs8zhN.png)

**Step 2：Add Line 15, 16 and 17 in “containers” section**
```javascript=
vim ~/ric-dep/helm/e2term/templates/deployment.yaml
```
```javascript=
    spec:
      hostname: {{ include "common.name.e2term" $topCtx }}-{{ $key }}
      hostNetwork: {{ .hostnetworkmode }}
      dnsPolicy: ClusterFirstWithHostNet
      imagePullSecrets:
        - name: {{ include "common.dockerregistry.credential" $imagectx }}
      {{- with .nodeselector }}
      nodeSelector: {{ toYaml . | trim | nindent 8 -}}
      {{- end }}
      containers:
        - name: {{ include "common.containername.e2term" $topCtx }}
          image: {{ include "common.dockerregistry.url" $imagectx }}/{{ .image.name }}:{{ .image.tag }}
          imagePullPolicy: {{ include "common.dockerregistry.pullpolicy" $pullpolicyctx }}
          volumeMounts:
          - mountPath: "{{ $common_env.ConfigMapName }}"
            name: local-router-file
            subPath: log-level
            ...
            ...
```
![](https://i.imgur.com/xJPCkXv.png)
**Step 3：Add log-level section**
```javascript=
vim ~/ric-dep/helm/e2term/templates/configmap.yaml
```
```javascript=
data:
  log-level: |
    {{- if hasKey .Values "loglevel" }}
    log-level: {{ .Values.loglevel }}
    {{- else }}
    log-level: 1
    {{- end }}
  rmr_verbose: |
    0
  ...
  ...
```
- Add Line from 2 to 7
![](https://i.imgur.com/5TT7ClZ.png)

## 5. Modify the code of Subscription Manager
### 5.1 Modify the Log-Level
**Change level from 3(Info) to 4(Debug)：**
```javascript=
vim ~/ric-dep/helm/submgr/templates/configmap.yaml
```
```javascript=
data:
  # FQDN and port info of rtmgr
  submgrcfg: |
    "local":
      "host": ":8080"
    "logger":
      "level": 4
    "rmr":
      "protPort" : "tcp:4560"
      "maxSize": 8192
      "numWorkers": 1
```
![](https://i.imgur.com/8mqFNDi.png)

### 5.2 Component Connection
**Step 1：Add new port for subscription in service file**
```javascript=
vim ~/ric-dep/helm/submgr/templates/service-http.yaml
```
```javascript=
spec:
  selector:
    app: {{ include "common.namespace.platform" . }}-{{ include "common.name.submgr" . }}
    release: {{ .Release.Name }}
  clusterIP: None
  ports:
  - name: http
    port: {{ include "common.serviceport.submgr.http" . }}
    protocol: TCP
    targetPort: http
  - name: subscription
    port: 8088
    protocol: TCP
    targetPort: 8088
```
- Add Line from 11 to 14
![](https://i.imgur.com/2UGmA5l.png)

**Step 2：Add new port for subscription in deployment file**
```javascript=
vim ~/ric-dep/helm/submgr/templates/deployment.yaml
```
```javascript=
containers:
          ...
          envFrom:
            - configMapRef:
                name: {{ include "common.configmapname.submgr" . }}-env
            - configMapRef:
                name: {{ include "common.configmapname.dbaas" . }}-appconfig
          ports:
            - name: subscription
              containerPort: 8088
              protocol: TCP
	    ...
```
- Add Line from 9 to 11
![](https://i.imgur.com/kXW6ZCg.png)

## 6. Modify the code of Routing Manager
### 6.1 Routing Path Configuration
**Add A1EI Msgtype and A1EI Routes：**
```javascript=
vim ~/ric-dep/helm/rtmgr/templates/config.yaml
```
```javascript=
       "messagetypes": [
          ...
          "A1_EI_QUERY_ALL=20013",
          "A1_EI_QUERY_ALL_RESP=20014",
          "A1_EI_CREATE_JOB=20015",
          "A1_EI_CREATE_JOB_RESP=20016",
          "A1_EI_DATA_DELIVERY=20017",
          ]
          ...
      "PlatformRoutes": [
         ...
         { 'messagetype': 'A1_EI_QUERY_ALL','senderendpoint': '', 'subscriptionid': -1, 'endpoint': 'A1MEDIATOR', 'meid': ''},
         { 'messagetype': 'A1_EI_CREATE_JOB','senderendpoint': '', 'subscriptionid': -1, 'endpoint': 'A1MEDIATOR', 'meid': ''},
          ]

```
- Add Line from 3 to 7 & 12 to 13
![](https://i.imgur.com/ThDhIrm.png)

## 7. Modify the code of Alarm Manager
### 7.1 Component Connection
**Step 1：Change controls.promAlertManager.address**
```javascript=
vim ~/ric-dep/helm/alarmmanager/templates/configmap.yaml
```
```javascript=
controls": {
        "promAlertManager": {
          "address": "r4-infrastructure-prometheus-alertmanager:80",
          "baseUrl": "api/v2",
          "schemes": "http",
          "alertInterval": 30000
        },

```
- change `cpro-alertmanager:80` to `r4-infrastructure-prometheus-alertmanager:80`
![](https://i.imgur.com/oqBY7FZ.png)

**Step 2：Add livenessProbe and readinessProbe**
```javascript=
vim ~/ric-dep/helm/alarmmanager/templates/deployment.yaml
```
```javascript=
    spec:
      hostname: {{ include "common.name.alarmmanager" . }}
      imagePullSecrets:
        - name: {{ include "common.dockerregistry.credential" $imagectx }}
      serviceAccountName: {{ include "common.serviceaccountname.alarmmanager" . }}
      containers:
        - name: {{ include "common.containername.alarmmanager" . }}
          image: {{ include "common.dockerregistry.url" $imagectx }}/{{ .Values.alarmmanager.image.name }}:{{ $imagetag }}
          imagePullPolicy: {{ include "common.dockerregistry.pullpolicy" $pullpolicyctx }}
          readinessProbe:
            failureThreshold: 3
            httpGet:
              path: ric/v1/health/ready
              port: 8080
              scheme: HTTP
            initialDelaySeconds: 5
            periodSeconds: 15
          livenessProbe:
            failureThreshold: 3
            httpGet:
              path: ric/v1/health/alive
              port: 8080
              scheme: HTTP
            initialDelaySeconds: 5
            periodSeconds: 15
          ...
```
- Add Line from 10 to 25
![](https://i.imgur.com/Zj0iGCs.png)

## 8. Modify the code of O1 Mediator
### 8.1 Component Connection
**Add livenessProbe and readinessProbe：**
```javascript=
vim ~/ric-dep/helm/o1mediator/templates/deployment.yaml
```
```javascript=
spec:
      hostname: {{ include "common.name.o1mediator" . }}
      imagePullSecrets:
        - name: {{ include "common.dockerregistry.credential" $imagectx }}
      serviceAccountName: {{ include "common.serviceaccountname.o1mediator" . }}
      containers:
        - name: {{ include "common.containername.o1mediator" . }}
          image: {{ include "common.dockerregistry.url" $imagectx }}/{{ .Values.o1mediator.image.name }}:{{ .Values.o1mediator.image.tag }}
          imagePullPolicy: {{ include "common.dockerregistry.pullpolicy" $pullpolicyctx }}
          livenessProbe:
            failureThreshold: 3
            httpGet:
              path: ric/v1/health/alive
              port: 8080
              scheme: HTTP
            initialDelaySeconds: 5
            periodSeconds: 15
            successThreshold: 1
            timeoutSeconds: 1
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
          ...
```
- Add Line from 10 to 29
![](https://i.imgur.com/KlBDCnr.png)

