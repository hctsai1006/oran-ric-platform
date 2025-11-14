# [F] SMO to [G] O-DU Slice Enable Scheduler with O1 Enable
:::info
**Outline:**
[TOC]

**Reference:**
- [[F] O-DU High With O1 Enabled](https://hackmd.io/tmTNEE7ET4S8mt3G6wCJzA#F-O-DU-High-With-O1-Enabled)
- [Connect [F] SMO and [F] O-DU via NetConf (O1) over TLS](https://hackmd.io/uD6uq1zfQx2JplBVmT32zA)
- [ONAP-based SMO Deployment](https://hackmd.io/@chengyu0415/S1ZRgwjxs)
- [O1VES使用說明](https://hackmd.io/Hw7LhuyuTzWFNifY2g0tFQ?view)
- [O-RAN SC VES Collector Study and usecase](https://hackmd.io/@chengyu0415/HypkVzXHn)
- [O1Ves 添加stnd defined event](https://hackmd.io/HBMhlIy_TVijRjioJn2n8w)

:::

:::success
**Goal:**
- [x] 1. [Installation of [G] O-DU Slice Enable Scheduler with O1 Enable](#Install-G-O-DU-Slice-Enable-Scheduler-with-O1-Enable)
- [x] 2. [Connect [F] SMO to [G] O-DU Slice Enable Scheduler with O1 Enable via NetConf (O1) over TLS](#Connect-F-SMO-to-G-O-DU-Slice-Enable-Scheduler-with-O1-Enable-via-NetConf-O1-over-TLS)
    - [x] 2.1 [Fix [F] SMO pods Init:CrashLoopBackOff can't reload issue.](#Check-whether-F-SMO-can-use-or-not)
    - [x] 2.2 [Established the connection ](#Result1)
- [x] 3. [Figure out how O-DU wraps data into VES Agent to VES Collector.](#How-O-DU-wraps-data-into-VES-Agent-to-VES-Collector)
- [x] 4. [Reporting PM to InfluxDB.](#Result4)
    - [x] 4.1 [Deploy InfluxDB, InfluxDB adapter and Grafana](#Result2)
    - [x] 4.2 [[G] O-DU sent VES Event to VES Collector](#Result3)
    - [x] 4.3 [Saving the VES Event in InfluxDB](#Result4)
- [x] 5. [Reporting PM on Grafana and show the PM charts on dashboard.](#Result6)
    - [x] 5.1 [Reporting PM on Grafana](#Result5)
    - [x] 5.2 [Show the PM charts on dashboard](#Result6)

:::
## Architecture 
![](https://hackmd.io/_uploads/S1lqZcYSn.png)

## Network Slicing procedure
![](https://hackmd.io/_uploads/B1T3W9KB2.png)

## Install [G] O-DU Slice Enable Scheduler with O1 Enable
:::info
:bulb: Refer this note: [**[F] O-DU High With O1 Enabled Installation Guide**](https://hackmd.io/tmTNEE7ET4S8mt3G6wCJzA).
:::

### Upgrade netopeer2 to libyang1 branch and Sysrepo
- File: `build/scripts/install_lib_O1.sh`

```shell=144
##    git clone -b v1.4.70 --depth 1  https://github.com/sysrepo/sysrepo.git && \
      git clone -b v1.4.140 --depth 1 https://github.com/sysrepo/sysrepo.git && \
```

``` shell=173
##    git clone -b v1.1.76 --depth 1 https://git-ntustoran.ddns.net/oran/netopeer2.git && \
      git clone -b libyang1 --depth 1 https://git-ntustoran.ddns.net/oran/netopeer2.git && \
```


### Change sysrepo from v1.4.70 to v1.4.140 supported

**1. File: `build/common/o1.mak`**
```shell=32
## lib: $(LIB_DIR)/libo1.a
lib: $(LIB_DIR)/libo1.a $(LIB_DIR)/libsysrepo_extend.so
```
- In line 48 add these code.
```shell=48
$(OBJ_DIR)/sysrepo_extend.o: $(SRC_DIR)/sysrepo_extend.cpp
	$(LINK.c) $(LDFLAGS) $(L_OPTS) $(I_OPTS) -fPIC -c $^ -o $@
$(LIB_DIR)/libsysrepo_extend.so: $(OBJ_DIR)/sysrepo_extend.o; $(LINK.c) $(LDFLAGS) $(L_OPTS) $(I_OPTS) -shared $^ -o $@
```

**2. File: `build/odu/makefile`**
```shell=129
  L_OPTS+= -lnetconf2 -lcjson -lcurl
  L_OPTS+=-lstdc++
  L_OPTS+=-lsysrepo_extend
```
```shell=207
link_du: du
##		   $(Q)$(CC1) -g -o $(OBJ_ROOT)/odu/odu -Wl,-R../lib/:. $(OBJ_ROOT)/odu/*.o\
##			$(L_OPTS) -L$(LIB_ROOT)/odu -L$(ROOT_DIR)/libs/odu 
                  $(Q)$(CC1) -L/usr/local/lib -g -o $(OBJ_ROOT)/odu/odu -Wl,-R../lib/:. $(OBJ_ROOT)/odu/*.o\
			$(L_OPTS) -L$(LIB_ROOT)/odu -L$(ROOT_DIR)/libs/odu
```
```shell=273
link_cu: 
##		$(Q)$(CC1) -g -o $(OBJ_ROOT)/cu_stub/cu_stub -Wl,-R../lib/:. $(OBJ_ROOT)/cu_stub/*.o\
               $(Q)$(CC1) -L/usr/local/lib -g -o $(OBJ_ROOT)/cu_stub/cu_stub -Wl,-R../lib/:. $(OBJ_ROOT)/cu_stub/*.o\
```

**3. Folder: `src/o1`**
- I edit some file in this file, you can download the [o1 folder](https://drive.google.com/file/d/1xdK_DUxgZxD82Fx2dT--dr8taQ-B9dqS/view?usp=share_link) directly. (Suggest you don't need to delete original folder just rename the folder.)

### Compile the cu_stub has some error
**1. File: `src/cu_stub/cu_stub.c`**
```shell=144
#ifdef O1_ENABLE
   if( getStartupConfigForStub(&g_cfg) != ROK )
   {
      DU_LOG("\nError  -->  CU_STUB : Could not fetch startup "\
             "configurations from Netconf interface\n");
      exit(1);
   }
   
   cmInetAddr((S8*)g_cfg.DU_IPV4_Addr, &ipv4_du);
   cuCb.cuCfgParams.sctpParams.f1SctpInfo.destCb[0].destIpAddr.ipV4Addr = ipv4_du;
   cuCb.cuCfgParams.sctpParams.f1SctpInfo.destCb[0].destIpAddr.ipV6Pres = false;
   
   cmInetAddr((S8*)g_cfg.CU_IPV4_Addr, &ipv4_cu);
   cuCb.cuCfgParams.sctpParams.localIpAddr.ipV4Addr = ipv4_cu;
   cuCb.cuCfgParams.sctpParams.localIpAddr.ipV6Pres = false;
   
   cuCb.cuCfgParams.sctpParams.f1SctpInfo.destCb[0].destPort = g_cfg.DU_Port;
   cuCb.cuCfgParams.sctpParams.f1SctpInfo.port = g_cfg.CU_Port; 
   cuCb.cuCfgParams.sctpParams.f1SctpInfo.numDestNode = 1;
   
   cuCb.cuCfgParams.egtpParams.localIp.ipV4Pres = TRUE;
   cuCb.cuCfgParams.egtpParams.localIp.ipV4Addr = ipv4_cu;
   cuCb.cuCfgParams.egtpParams.localPort = F1_EGTP_PORT;
   cuCb.cuCfgParams.egtpParams.dstCfg[0].dstIp.ipV4Pres = TRUE;
   cuCb.cuCfgParams.egtpParams.dstCfg[0].dstIp.ipV4Addr = ipv4_du;
   cuCb.cuCfgParams.egtpParams.dstCfg[0].dstPort = F1_EGTP_PORT;
   cuCb.cuCfgParams.egtpParams.minTunnelId = MIN_TEID;
   cuCb.cuCfgParams.egtpParams.currTunnelId = cuCb.cuCfgParams.egtpParams.minTunnelId;
   cuCb.cuCfgParams.egtpParams.maxTunnelId = MAX_TEID;
   cuCb.cuCfgParams.egtpParams.numDu = 1;
```
**2. File: `src/cu_stub/cu_f1ap_msg_hdl.c`**
```shell=12039
##if(LOCAL_NODE_TYPE == CLIENT)
##      BuildAndSendXnSetupReq();
```

### Result
:::success
:bulb: **More details about cu_stub, ric_stub, odu [LOG](https://drive.google.com/drive/folders/1ZjFell48zsBmO1T72mC4p5x90ZPZYwpX?usp=sharing)**
:::
- cu_stub
![](https://hackmd.io/_uploads/ByHRC-AS2.png)

- ric_stub
![](https://hackmd.io/_uploads/HJgx4JMCSh.png)

- odu
![](https://hackmd.io/_uploads/SJAmSwPS3.png)

### Alarm Check
![](https://hackmd.io/_uploads/ryhr-fRSn.png)



---

## Connect [F] SMO to [G] O-DU Slice Enable Scheduler with O1 Enable via NetConf (O1) over TLS

:::info
:bulb: Refer this note: [**Connect \[F\] SMO and \[F\] O-DU via NetConf (O1) over TLS**](https://hackmd.io/uD6uq1zfQx2JplBVmT32zA).
:::

### Check whether [F] SMO can use or not
-   login to web console  
    login to url: https://<your host ip/>:30205/odlux/index.html
```
user: admin
password: Kp8bJ4SXszM0WXlhak3eHlcse2gAw84vaoGGmJvUy2U
```
    
:::danger
:memo: **Issue:** Pods Init:CrashLoopBackOff can't reload and restart, web console can't work.

![](https://hackmd.io/_uploads/B1OIpo4Un.png)

:::success
:heavy_check_mark: **Solution:**

```bash=
cd workspace
sudo su
.dep/smo-install/scripts/uninstall-all.sh    
    
## Setup Helm charts
./dep/smo-install/scripts/layer-0/0-setup-charts-museum.sh
./dep/smo-install/scripts/layer-0/0-setup-helm3.sh
./dep/smo-install/scripts/layer-1/1-build-all-charts.sh
## Deploy components
./dep/smo-install/scripts/layer-2/2-install-oran.sh
    
## wait for pod finished
kubectl get pods -n onap
## Deploy simulators (DU/RU simulators)
./dep/smo-install/scripts/layer-2/2-install-simulators.sh
```
![](https://hackmd.io/_uploads/ryaiVm-82.png)
    
![](https://hackmd.io/_uploads/ByjPrKbIh.png)

:::


    
### Result

![](https://hackmd.io/_uploads/HkM5pNW8n.png)

----
## Deployment of dmaap-InfluxDB-adapter, InfluxDB and Grafana

:::info
:bulb: Refer this note: [**O1VES使用說明**](https://hackmd.io/Hw7LhuyuTzWFNifY2g0tFQ?view).
- **Here I use Helm to deploy.**
:::

### Pre-Request 
- Finished the installation of ONAP SMO.
### Deploy
- Helm repo add and install
```bash=
helm repo add winlab https://harbor.winfra.cs.nycu.edu.tw/chartrepo/winlab-oran
helm install --namespace=o1ves o1ves winlab/o1ves-visualization --create-namespace
```

:::warning
:red_circle: **NOTE:** Using a release name other than o1ves may cause unexpected errors.
:::

- Edit the `values.yaml` file
```bash=
helm show values winlab/o1ves-visualization > values.yaml
```
:::info
- Modify the **rules**.
- Add buckets to automatically create influxdb buckets.
:::

#### `values.yaml`
- For example:
```yaml=
fullnameOverride: o1ves

grafana:
  fullnameOverride: o1ves-grafana
  enabled: true
  defaultDashboardsTimezone: Asia/Taipei
  adminPassword: smo
  service:
    type: NodePort
    nodePort: 30000
  persistence:
    enabled: true
    storageClassName: "local-storage-grafana"
    size: 10Gi

influxdb2:
  fullnameOverride: o1ves-influxdb2
  enabled: true
  persistence:
    enabled: true
    storageClass: "local-storage-influxdb2"
    accessMode: ReadWriteOnce
    size: 50Gi
    mountPath: /var/lib/influxdb2
    subPath: ""
  image:
    repository: influxdb
    tag: 2.3.0-alpine
    pullPolicy: IfNotPresent

dmaap-influxdb-adapter:
  enabled: true
  image: 
    repository: harbor.winfra.cs.nycu.edu.tw/winlab-oran/dmaap-influxdb-adapter
  influxdb: 
    host: o1ves-influxdb2
    port: 80
    tokenSecret: o1ves-influxdb2-auth
    org: influxdata
  logLevel: DEBUG

  rules: 
    - topic: unauthenticated.SEC_FAULT_OUTPUT
      rules:
        - bucket: influxdb
          measurement: fault
          matches: 
            - key: event.commonEventHeader.domain
              value: fault
          tags:
            - key: type
              value: test
            - key: sourceId
              field: event.commonEventHeader.sourceId
          fields:
            - key: faultFieldsVersion
              field: event.faultFields.faultFieldsVersion
              type: string

buckets:
  - name: influxdb

image:
  pullPolicy: IfNotPresent

```
### Delete 
```bash=
helm uninstall --namespace o1ves o1ves  
kubectl delete ns o1ves
sudo rm -r /dockerdata-nfs/o1ves-*
```

:::warning
#### :red_circle: **NOTE:**
- If you edit the `values.yaml` , you need to **upgrade the pod** or delete and redeploy.
```bash=
## Upgrade
helm upgrade --namespace=o1ves o1ves winlab/o1ves-visualization --create-namespace -f value2.yml

## Redeploy
helm uninstall --namespace o1ves o1ves  
kubectl delete ns o1ves
sudo rm -r /dockerdata-nfs/o1ves-*
helm install --namespace=o1ves o1ves winlab/o1ves-visualization --create-namespace -f values.yaml
```
- You can write a ves event then use this command to test sent the event to influxdb.
```bash=
curl -X POST \
   -H 'Content-Type: application/json' \
   -u sample1:sample1 \
   -d @file.json \
   https://192.168.8.229:30417/eventListener/v7
```
- Check whether influxdb-adapter receive the event or not.
```bash=
kubectl logs -n o1ves o1ves-dmaap-influxdb-adapter-64cf8bf7b8-qf6sg 
```
:::

### InfluxDB, Grafana Web UI and Set InfluxDB Data Source
#### InfluxDB Web UI
- http://<server-ip/>:30001
> Here we use http://192.168.8.229:30001

- username and password : (admin/)


:::warning
- If InfluxDB port didn't open, you can refer this.
```bash=
kubectl edit svc -n o1ves o1ves-influxdb2
# line 33 add: nodePort:30001
# line 41 type change to NodePort
```
- Use this command to find the password.
```bash=
kubectl get secret -n o1ves o1ves-influxdb2-auth -o json
# find the password then echo
echo OGMwdDRYRG1xUXNyR29BQ3hCZFdVZkZGeGJqUlRpTlc= | base64 -d
```

:::

#### Grafana Web UI
- http://<server-ip/>:30000
> Here we use http://192.168.8.229:30000
- username and password : (admin/smo)
#### Set influxdb data source
- Go Administration/Data sources you will see InfluxDB default.
    - Check the seeting:
        - Query Language: Flux
        - URL: http://o1ves-influxdb2.o1ves
        - Auth
            -   Basic auth: Disable
        - InfluxDB Details
            -   Organization: influxdb
            -   Token: my-token
- Save & test

### Result
- Check pods are running

![](https://hackmd.io/_uploads/ryaAJSJv2.png)

- InfluxDB Web UI

![](https://hackmd.io/_uploads/ryMHCeNY2.png)

- Grafana Web UI

![](https://hackmd.io/_uploads/rJlJmrJPh.png)

----
## [G] O-DU sent VES Event to VES Collector
### VES Collector
- Requires additional settings.
- Reference: [O1 Ves 添加Stnd defined event](https://hackmd.io/HBMhlIy_TVijRjioJn2n8w)

1. Apply config map
```bash=
kubectl apply -f configmap.yml
```
:::spoiler configmap.yml
```=
apiVersion: v1
kind: ConfigMap
metadata:
  name: ves-collector-extra
  namespace: onap
data:
  schema-map.json: |
    [
      {
        "publicURL": "https://forge.3gpp.org/rep/sa5/MnS/blob/SA88-Rel16/OpenAPI/faultMnS.yaml",
        "localURL": "3gpp/rep/sa5/MnS/blob/SA88-Rel16/OpenAPI/faultMnS.yaml"
      },
      {
        "publicURL": "https://forge.3gpp.org/rep/sa5/MnS/blob/SA88-Rel16/OpenAPI/heartbeatNtf.yaml",
        "localURL": "3gpp/rep/sa5/MnS/blob/SA88-Rel16/OpenAPI/heartbeatNtf.yaml"
      },
      {
        "publicURL": "https://forge.3gpp.org/rep/sa5/MnS/blob/SA88-Rel16/OpenAPI/PerDataFileReportMnS.yaml",
        "localURL": "3gpp/rep/sa5/MnS/blob/SA88-Rel16/OpenAPI/PerDataFileReportMnS.yaml"
      },
      {
        "publicURL": "https://forge.3gpp.org/rep/sa5/MnS/blob/SA88-Rel16/OpenAPI/provMnS.yaml",
        "localURL": "3gpp/rep/sa5/MnS/blob/SA88-Rel16/OpenAPI/provMnS.yaml"
      },
      {
        "publicURL": "https://gerrit.o-ran-sc.org/r/gitweb?p=scp/oam/modeling.git;a=blob_plain;f=data-model/oas3/experimental/o-ran-sc-du-hello-world-pm-streaming-oas3.yaml",
        "localURL": "extra/o-ran-sc-du-hello-world-pm-streaming-oas3.yaml"
      }
    ]
  o-ran-sc-du-hello-world-pm-streaming-oas3.yaml: |
    openapi: 3.0.3
    info:
      version: 0.0.0
      title: O-RAN-SC-DU PM Streaming
      description: >-
        The O-RAN-SC E-Release provides a mechanism for Performance Measurement
        streaming.


        The streaming interfaces depends on the o-ran-sc-du-hello-world.yang and
        the schemas could be used as extension sot the VES domain 'stndDefind'.
        The event message is send from a network-function to a SMO.


        Copyright 2021 highstreet technologies GmbH


        Licensed under the Apache License, Version 2.0 (the "License");
        you may not use this file except in compliance with the License.
        You may obtain a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

        Unless required by applicable law or agreed to in writing, software
        distributed under the License is distributed on an "AS IS" BASIS,
        WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
        See the License for the specific language governing permissions and
        limitations under the License.


        reference: https://jira.o-ran-sc.org/browse/OAM-234.

    servers:
      - url: https://management-service-consumer:8443/v1
        description: The url of an event stream consumer.
    paths:
      /performance-measurement-stream:
        post:
          description: Posts a collection of measurements.
          summary: POST performance-measurement-stream
          requestBody:
            content:
              application/json:
                schema:
                  $ref: '#/components/schemas/performance-measurement-job'
            description: Collection of measurements.
          responses:
            '201':
              description: Posted
            '400':
              description: Bad Request
              content:
                application/json:
                  schema:
                    $ref: '#/components/schemas/error-response'
            '401':
              description: Unauthorized
              content:
                application/json:
                  schema:
                    $ref: '#/components/schemas/error-response'
            '403':
              description: Forbidden
              content:
                application/json:
                  schema:
                    $ref: '#/components/schemas/error-response'
            '404':
              description: Not Found
              content:
                application/json:
                  schema:
                    $ref: '#/components/schemas/error-response'
            '405':
              description: Method Not allowed
              content:
                application/json:
                  schema:
                    $ref: '#/components/schemas/error-response'
            '409':
              description: Conflict
              content:
                application/json:
                  schema:
                    $ref: '#/components/schemas/error-response'
            '500':
              description: Internal Server Error
              content:
                application/json:
                  schema:
                    $ref: '#/components/schemas/error-response'
            default:
              description: Error case.
              content:
                application/json:
                  schema:
                    $ref: '#/components/schemas/error-response'
    components:
      schemas:
        error-response:
          description: >-
            Used when an API throws an error with a HTTP error response-code (3xx,
            4xx, 5xx)
          type: object
          required:
            - reason
          properties:
            reason:
              type: string
              description: >-
                Explanation of the reason for the error which can be shown to a
                human user.
            message:
              type: string
              description: >-
                More details and corrective actions related to the error which can
                be shown to a human user.
            documentation-reference:
              type: string
              format: uri
              description: URI of describing the error.
        measurement:
          description: An abstract object class of a measurement.
          type: object
          required:
            - measurement-type-instance-reference
            - value
          properties:
            measurement-type-instance-reference:
              type: string
              description: >-
                A YANG instance identifier for a supported measurement type
                according to the definitions in o-ran-sc-du-hello-world.yang.

                Example for average downlink user equipment throughput per cell
                /network-function/distributed-unit-functions[id='<id-value>']/cell[id='<id-value']/supported-measurements/performance-measurement-type[.='user-equipment-average-throughput-downlink']

                Example for a specific slice-differentiator (here sd=12345) subcounter of average downlink user equipment throughput
                /network-function/distributed-unit-functions[id='<id-value>']/cell[id='<id-value']/supported-measurements/performance-measurement-type[.='user-equipment-average-throughput-downlink']/supported-snssai-subcounter-instances/slice-differentiator[.=12345]";
            value:
              anyOf:
                - type: boolean
                  description: A boolean value for the measurement.
                - type: integer
                  description: A integer value for the measurement.
                - type: number
                  description: A number value for the measurement.
                - type: string
                  description: A string value for the measurement.
              description: 'The value of the measurement type for its period. '
            unit:
              type: string
              maxLength: 255
              description: >-
                The unit for the measurement. If there is a unit associated to the
                measurement the network-function MUST provide this field. It is
                recommended to follow International System of Units (SI).
        measurements:
          description: A collection of measurements.
          type: array
          items:
            $ref: '#/components/schemas/measurement'
        performance-measurement-job:
          description: The performance measurement job header and a collection of measurements.
          type: object
          required:
            - id
            - start-time
            - granularity-period
            - measurements
          properties:
            id:
              type: string
              description: >-
                The identifier configured by the event stream consumer within a
                event stream provider for a performance-measurement-job.
            start-time:
              type: string
              format: date-time
              description: 'The timestamp when the measurement was started. '
            administrative-state:
              description: >-
                Administrative state of an object. Indicates the permission to use
                or prohibition against the object, imposed through the OAM services.
              type: string
              default: locked
              enum:
                - locked
                - unlocked
                - shutting-down
            operational-state:
              type: string
              default: disabled
              enum:
                - enabled
                - disabled
              description: >-
                Operational state of the object. Indicates whether the associated
                resource is installed and partially or fully operable (enabled) or
                the associated resource is not installed or not operable (disabled).
            user-label:
              type: string
              maxLength: 255
              description: >-
                A user defined label of the object. There is no function associated
                to the user label. However, the network function stores the value
                persistently.
            job-tag:
              type: string
              maxLength: 255
              description: >-
                A job group identifier to combine several
                performance-measurement-jobs to one logical job.
            granularity-period:
              type: number
              format: int32
              description: >-
                The interval time in seconds between the start of a measurement and
                the end of a measurement
            measurements:
              $ref: '#/components/schemas/measurements'
              description: The collection of measurements.
```
:::
<br>

2. Update ves collector config
```bash=
helm get values -n onap onap-dcaegen2-services > dcaegen2.values.yml
```
- `dcaegen2.values.yml`，edit dcae-ves-collector part
```
dcae-ves-collector:
  enabled: true
  externalVolumes:
    - name: ves-collector-extra
      type: configmap
      mountPath: /opt/app/VESCollector/etc/externalRepo/extra
  applicationConfig:
    collector.dmaap.streamid: o-ran-sc-du-hello-world-pm-streaming-oas3=ves-measurement|fault=ves-fault|syslog=ves-syslog|heartbeat=ves-heartbeat|measurement=ves-measurement|measurementsForVfScaling=ves-measurement|mobileFlow=ves-mobileflow|other=ves-other|stateChange=ves-statechange|thresholdCrossingAlert=ves-thresholdCrossingAlert|voiceQuality=ves-voicequality|sipSignaling=ves-sipsignaling|notification=ves-notification|pnfRegistration=ves-pnfRegistration|3GPP-FaultSupervision=ves-3gpp-fault-supervision|3GPP-Heartbeat=ves-3gpp-heartbeat|3GPP-Provisioning=ves-3gpp-provisioning|3GPP-PerformanceAssurance=ves-3gpp-performance-assurance
    collector.externalSchema.mappingFileLocation: "./etc/externalRepo/extra/schema-map.json"
```
- Upgrade
```bash=
cd dep/smo-install/scripts/layer-0
chartmuseum --port=18080 --storage="local" --storage-local-rootdir=../../../chartstorage &
cd
helm upgrade -f dcaegen2.values.yml -n onap onap-dcaegen2-services local/dcaegen2-services
```


### O-DU 
- When you push cell up at O-DU side via NetConf, it will start to sent the VES Event to VES Collector.
- Reference: [Push cell and slice configuration over O1 using netopeer-cli](https://hackmd.io/tmTNEE7ET4S8mt3G6wCJzA?view#Push-cell-and-slice-configuration-over-O1-using-netopeer-cli)
### Check
- Use this command to check whether VES Collector recievd the data or not.

```bash=
kubectl logs -n onap onap-dcae-ves-collector-6fcfc6c9d5-5b99v -f
```

### Result

![](https://hackmd.io/_uploads/SkEDM7ID3.png)

:::danger
:memo: **Issue 01:** 

- StndDefinedSchemaValidator . thresholdInfo.observedValue : Type expected 'integer', found 'number'. (code: 1027)
- StndDefinedSchemaValidator .thresholdInfo.obse rvedValue: Type expected 'string', found 'number'.  (code: 1027)
- StndDefinedSchemaValidator.stateChangeDefinition: Type expected 'object', found 'array'. ( (code: 1027)

![](https://hackmd.io/_uploads/SkD6YTHP3.png)

:::success
:heavy_check_mark: **Solution:**

**File:**
`/home/oran/slice_enable_scheduler/src/o1/ves/JsonHelper.cpp`
- In line 93: Coercion the type.
```bash=90
cJSON* JsonHelper::addNodeToObject(cJSON * parent, \
                                          const char * nodeName, double value)
{
   return cJSON_AddNumberToObject(parent, nodeName, (int) value);
}
```
**File:** `/home/oran/slice_enable_scheduler/src/o1/ves/CellStateChangeStdDef.cpp`

- In line 215 to line 220: Use /* to annotation.
- Then add these codes.
```bash=215
/*cJSON*  stateChangeDefinitionArr= cJSON_CreateArray();
   if (stateChangeDefinitionArr == NULL)
   {
      ret = false;
   }
   cJSON_AddItemToObject(data, "stateChangeDefinition", stateChangeDefinitionArr);*/

   cJSON*  stateChangeDefinitionObj= cJSON_CreateObject();
   if (stateChangeDefinitionObj == NULL)
   {
      ret = false;
   }
   cJSON_AddItemToObject(data, "stateChangeDefinition", stateChangeDefinitionObj);
```
:::



:::danger
:memo: **Issue 02:** 
- ERROR 24 \[nio-8443-exec-2\] o.o.d.r.VesRestcontroller :org.onap.dcaegen2.services.sk.services.external.schema.manager.exception.NoLocalReferenceException:Couldn't find mapping for public ur1. PublicURL: https://gerrit.o-ran-sc.org/r/gitweb?p=scp/oam/modeling.git;a=blob_plain;f=data-mode1/oas3/experimental/o-ran-sc-du-hel1o-world-p pm-streaming-oas3.yaml

![](https://hackmd.io/_uploads/SJ3-iTrPh.png)

:::success
:heavy_check_mark: **Solution:**
- VES Collector requires additional settings.
- Reference: [O1 Ves 添加Stnd defined event](https://hackmd.io/HBMhlIy_TVijRjioJn2n8w)
- If you [already have and set `configmap.yml` and `dcaegen2.values.yml`](#VES-Collector), you can just use the following commands.

```bash=
kubectl apply -f configmap.yml
cd dep/smo-install/scripts/layer-0
chartmuseum --port=18080 --storage="local" --storage-local-rootdir=../../../chartstorage &
cd
helm upgrade -f dcaegen2.values.yml -n onap onap-dcaegen2-services local/dcaegen2-services
```
:::

:::danger
:memo: **Issue 03:** 
- Hang tight while we grab the latest from your chart repositories...
...Unable to get an update from the "local" chart repository (http://127.0.0.1:8879/charts):
        Get "http://127.0.0.1:8879/charts/index.yaml": dial tcp 127.0.0.1:8879: connect: connection refused

![](https://hackmd.io/_uploads/r1AF-7LP3.png)

:::success
:heavy_check_mark: **Solution:**

```bash=
helm repo remove local
helm repo add local http://localhost:18080
```
:::

----

## Saving the VES event in InfluxDB

:::info
:bulb: **Refer these notes:** 
- [O1VES使用說明](https://hackmd.io/Hw7LhuyuTzWFNifY2g0tFQ?view)
- [O1Ves 添加stnd defined event](https://hackmd.io/HBMhlIy_TVijRjioJn2n8w)
:::

### Set the rules
1. Edit the [`values.yaml`](#valuesyaml)
2. topic:
    - Find event `stndDefinedNamespace` [mapping DMAAP topic](#Mapping-to-DMAAP-topic)
3. According to your needs, to adjust 
    - bucket
    - measurement
    - matches
    - tags
    - fields


**VES event examples:**

:::spoiler VES Event 1
```shell=
O1 VesEvent : VES request : -- 
{
    "event":	{
        "commonEventHeader":	{
            "domain":	"stndDefined",
            "eventId":	"Alarm000000001",
            "eventName":	"COMMUNICATIONS_ALARM",
            "eventType":	"alarm",
            "sequence":	1,
            "priority":	"Low",
            "reportingEntityId":	"ODU-High",
            "reportingEntityName":	"ODU-High",
            "sourceId":	"device_id_cc305d54-75b4-431b-adb2-eb6b9e541234",
            "sourceName":	"ODU-High",
            "startEpochMicrosec":	1688352962696559,
            "lastEpochMicrosec":	1688352968696559,
            "nfNamingCode":	"7odu",
            "nfVendorName":	"POC",
            "nfcNamingCode":	"NFC",
            "timeZoneOffset":	"+00:00",
            "version":	"4.0.1",
            "stndDefinedNamespace":	"3GPP-FaultSupervision",
            "vesEventListenerVersion":	"7.2.1"
        },
        "stndDefinedFields":	{
            "schemaReference":	"https://forge.3gpp.org/rep/sa5/MnS/blob/SA88-Rel16/OpenAPI/faultMnS.yaml#components/schemas/NotifyNewAlarm",
            "data":	{
                "href":	"1",
                "uri":	"1",
                "notificationId":	1,
                "notificationType":	"notifyNewAlarm",
                "eventTime":	"2023-07-03T02:56:02Z",
                "systemDN":	"",
                "probableCause":	"device-issue",
                "perceivedSeverity":	"INDETERMINATE",
                "rootCauseIndicator":	false,
                "specificProblem":	"CELL UP",
                "correlatedNotifications":	[],
                "backedUpStatus":	true,
                "backUpObject":	"",
                "trendIndication":	"MORE_SEVERE",
                "thresholdInfo":	{
                    "observedMeasurement":	"new",
                    "observedValue":	123.2
                },
                "stateChangeDefinition":	[],
                "monitoredAttributes":	{
                    "newAtt":	"new"
                },
                "proposedRepairActions":	"Config change",
                "additionalText":	"CELL 1 UP",
                "additionalInformation":	{
                    "addInfo":	"CELL UP"
                },
                "alarmId":	"1009",
                "alarmType":	"COMMUNICATIONS_ALARM"
            },
            "stndDefinedFieldsVersion":	"1.0"
        }
    }
}

```
:::
<br>

:::spoiler VES Event 2 (Jacky)
```shell=
O1 VesEvent : VES request : -- 
{
    "event":	{
        "commonEventHeader":	{
            "domain":	"stndDefined",
            "eventId":	"pm1_1638984365",
            "eventName":	"stndDefined_performanceMeasurementStreaming",
            "eventType":	"performanceMeasurementStreaming",
            "sequence":	1,
            "priority":	"Low",
            "reportingEntityId":	"ODU-High",
            "reportingEntityName":	"ORAN-DEV",
            "sourceId":	"",
            "sourceName":	"ODU-High",
            "startEpochMicrosec":	1685550782620452,
            "lastEpochMicrosec":	1685550788620452,
            "nfNamingCode":	"7odu",
            "nfVendorName":	"POC",
            "nfcNamingCode":	"NFC",
            "timeZoneOffset":	"+00:00",
            "version":	"4.0.1",
            "stndDefinedNamespace":	"o-ran-sc-du-hello-world-pm-streaming-oas3",
            "vesEventListenerVersion":	"7.2.1"
        },
        "stndDefinedFields":	{
            "stndDefinedFieldsVersion":	"1.0",
            "schemaReference":	"https://gerrit.o-ran-sc.org/r/gitweb?p=scp/oam/modeling.git;a=blob_plain;f=data-model/oas3/experimental/o-ran-sc-du-hello-world-pm-streaming-oas3.yaml",
            "data":	{
                "id":	"pm1_1638984365",
                "start-time":	"2023-05-31T16:33:02Z",
                "administrative-state":	"unlocked",
                "operational-state":	"enabled",
                "user-label":	"pm-1",
                "job-tag":	"",
                "granularity-period":	5,
                "measurements":	[{
                        "measurement-type-instance-reference":	"/o-ran-sc-du-hello-world:network-function/distributed-unit-functions[id='ODU-High']/cell[id='1']/supported-measurements[performance-measurement-type='user-equipment-average-throughput-downlink']/supported-snssai-subcounter-instances[slice-differentiator='1'][slice-service-type='1']",
                        "value":	0,
                        "unit":	"kbit/s"
                    }, {
                        "measurement-type-instance-reference":	"/o-ran-sc-du-hello-world:network-function/distributed-unit-functions[id='ODU-High']/cell[id='1']/supported-measurements[performance-measurement-type='user-equipment-average-throughput-uplink']/supported-snssai-subcounter-instances[slice-differentiator='1'][slice-service-type='1']",
                        "value":	0,
                        "unit":	"kbit/s"
                    }, {
                        "measurement-type-instance-reference":	"/o-ran-sc-du-hello-world:network-function/distributed-unit-functions[id='ODU-High']/cell[id='1']/supported-measurements[performance-measurement-type='user-equipment-average-throughput-downlink']/supported-snssai-subcounter-instances[slice-differentiator='2'][slice-service-type='1']",
                        "value":	0,
                        "unit":	"kbit/s"
                    }, {
                        "measurement-type-instance-reference":	"/o-ran-sc-du-hello-world:network-function/distributed-unit-functions[id='ODU-High']/cell[id='1']/supported-measurements[performance-measurement-type='user-equipment-average-throughput-uplink']/supported-snssai-subcounter-instances[slice-differentiator='2'][slice-service-type='1']",
                        "value":	0,
                        "unit":	"kbit/s"
                    }, {
                        "measurement-type-instance-reference":	"/o-ran-sc-du-hello-world:network-function/distributed-unit-functions[id='ODU-High']/cell[id='1']/supported-measurements[performance-measurement-type='user-equipment-average-throughput-downlink']/supported-snssai-subcounter-instances[slice-differentiator='224'][slice-service-type='135']",
                        "value":	0,
                        "unit":	"kbit/s"
                    }, {
                        "measurement-type-instance-reference":	"/o-ran-sc-du-hello-world:network-function/distributed-unit-functions[id='ODU-High']/cell[id='1']/supported-measurements[performance-measurement-type='user-equipment-average-throughput-uplink']/supported-snssai-subcounter-instances[slice-differentiator='224'][slice-service-type='135']",
                        "value":	0,
                        "unit":	"kbit/s"
                    }]
            }
        }
    }
}
```
:::

<br>

:::spoiler [ VES Event 3 (Akmal)](https://hackmd.io/gak6B2vuQs-x7alV4mJWgw?view#Result)
```shell=
O1 VesEvent : VES request : -- 
{
	"event":	{
		"commonEventHeader":	{
			"domain":	"stndDefined",
			"eventId":	"pm1_1638984365",
			"eventName":	"stndDefined_performanceMeasurementStreaming",
			"eventType":	"performanceMeasurementStreaming",
			"sequence":	1,
			"priority":	"Low",
			"reportingEntityId":	"ODU-High",
			"reportingEntityName":	"ORAN-DEV",
			"sourceId":	"",
			"sourceName":	"ODU-High",
			"startEpochMicrosec":	1696391705807124,
			"lastEpochMicrosec":	1696391711807124,
			"nfNamingCode":	"7odu",
			"nfVendorName":	"POC",
			"nfcNamingCode":	"NFC",
			"timeZoneOffset":	"+00:00",
			"version":	"4.0.1",
			"stndDefinedNamespace":	"o-ran-sc-du-hello-world-pm-streaming-oas3",
			"vesEventListenerVersion":	"7.2.1"
		},
		"stndDefinedFields":	{
			"stndDefinedFieldsVersion":	"1.0",
			"schemaReference":	"https://gerrit.o-ran-sc.org/r/gitweb?p=scp/oam/modeling.git;a=blob_plain;f=data-model/oas3/experimental/o-ran-sc-du-hello-world-pm-streaming-oas3.yaml",
			"data":	{
				"id":	"pm1_1638984365",
				"start-time":	"2023-10-04T03:55:05Z",
				"administrative-state":	"unlocked",
				"operational-state":	"enabled",
				"user-label":	"pm-1",
				"job-tag":	"",
				"granularity-period":	5,
				"measurements":	[{
						"measurement-type-instance-reference":	"/o-ran-sc-du-hello-world:network-function/distributed-unit-functions[id='ODU-High']/cell[id='1']/supported-measurements[performance-measurement-type='user-equipment-average-throughput-downlink']/supported-snssai-subcounter-instances[slice-differentiator='1'][slice-service-type='1']",
						"value":	5493104,
						"unit":	"kbit/s"
					}, {
						"measurement-type-instance-reference":	"/o-ran-sc-du-hello-world:network-function/distributed-unit-functions[id='ODU-High']/cell[id='1']/supported-measurements[performance-measurement-type='user-equipment-MCS-Index']/supported-snssai-subcounter-instances[slice-differentiator='1'][slice-service-type='1']",
						"value":	17.806722689075631,
						"unit":	""
					}]
			}
		}
	}
}
```
:::

#### Mapping to DMAAP topic

:::info

1. Check the applicationConfig table

| stndDefinedNamespace | collector.dmaap.streamid |
| -------- | -------- |
|o-ran-sc-du-hello-world-pm-streaming-oas3|ves-measurement|
|fault|ves-fault|
|syslog|ves-syslog|
|heartbeat|ves-heartbeat|
|measurement|ves-measurement|
|measurementsForVfScaling|ves-measurement|
|mobileFlow|ves-mobileflow|
|other|ves-other|
|stateChange|ves-statechange|
|thresholdCrossingAlert|ves-thresholdCrossingAlert|
|voiceQuality|ves-voicequality|
|sipSignaling|ves-sipsignaling|
|notification|ves-notification|
|pnfRegistration|ves-pnfRegistration|
|3GPP-FaultSupervision|ves-3gpp-fault-supervision|
|3GPP-Heartbeat|ves-3gpp-heartbeat|
|3GPP-Provisioning|ves-3gpp-provisioning|
|3GPP-PerformanceAssurance|ves-3gpp-performance-assurance|

2. VES ID to DMAAP topic mapping
    - `topic_url: http://message-router:3904/events/{topicname}`

3. Find the topic name

```
streams_publishes:
  ves-3gpp-fault-supervision:
    dmaap_info:
      topic_url: http://message-router:3904/events/unauthenticated.SEC_3GPP_FAULTSUPERVISION_OUTPUT
    type: message_router
  ves-3gpp-heartbeat:
    dmaap_info:
      topic_url: http://message-router:3904/events/unauthenticated.SEC_3GPP_HEARTBEAT_OUTPUT
    type: message_router
  ves-3gpp-performance-assurance:
    dmaap_info:
      topic_url: http://message-router:3904/events/unauthenticated.SEC_3GPP_PERFORMANCEASSURANCE_OUTPUT
    type: message_router
  ves-3gpp-provisioning:
    dmaap_info:
      topic_url: http://message-router:3904/events/unauthenticated.SEC_3GPP_PROVISIONING_OUTPUT
    type: message_router
  ves-fault:
    dmaap_info:
      topic_url: http://message-router:3904/events/unauthenticated.SEC_FAULT_OUTPUT
    type: message_router
  ves-heartbeat:
    dmaap_info:
      topic_url: http://message-router:3904/events/unauthenticated.SEC_HEARTBEAT_OUTPUT
    type: message_router
  ves-measurement:
    dmaap_info:
      topic_url: http://message-router:3904/events/unauthenticated.VES_MEASUREMENT_OUTPUT
    type: message_router
  ves-notification:
    dmaap_info:
      topic_url: http://message-router:3904/events/unauthenticated.VES_NOTIFICATION_OUTPUT
    type: message_router
  ves-other:
    dmaap_info:
      topic_url: http://message-router:3904/events/unauthenticated.SEC_OTHER_OUTPUT
    type: message_router
  ves-pnfRegistration:
    dmaap_info:
      topic_url: http://message-router:3904/events/unauthenticated.VES_PNFREG_OUTPUT
    type: message_router
```

:::

#### In this case rules we use (Jacky):
```yaml
dmaap-influxdb-adapter:
  image:
    pullPolicy: Always
  logLevel: DEBUG
  rules:
    - topic: unauthenticated.VES_MEASUREMENT_OUTPUT
      rules:
        - bucket: my-bucket
          measurement: slice-measurement
          matches: 
            - key: event.commonEventHeader.domain
              value: stndDefined
          tags:
            - key: vendor
              value: ntust-taiwan-lab
            - key: sourceName
              field: event.commonEventHeader.sourceName
          fields:
            - key: slice-1-avg-throughput-downlink
              field: event.stndDefinedFields.data.measurements[0].value
              type: int
            - key: slice-1-avg-PRB-used-downlink
              field: event.stndDefinedFields.data.measurements[1].value
              type: int
            - key: slice-2-avg-throughput-downlink
              field: event.stndDefinedFields.data.measurements[2].value
              type: int
            - key: slice-2-avg-PRB-used-downlink
              field: event.stndDefinedFields.data.measurements[3].value
              type: int
            - key: slice-3-avg-throughput-downlink
              field: event.stndDefinedFields.data.measurements[4].value
              type: int
            - key: slice-3-avg-PRB-used-downlink
              field: event.stndDefinedFields.data.measurements[5].value
              type: int
buckets:
  - name: my-bucket
```

:::spoiler Rules (Akmal)
```yaml=
dmaap-influxdb-adapter:
  image:
    pullPolicy: Always
  logLevel: DEBUG
  rules:
    - topic: unauthenticated.VES_MEASUREMENT_OUTPUT
      rules:
        - bucket: my-bucket
          measurement: slice-measurement
          matches: 
            - key: event.commonEventHeader.domain
              value: stndDefined
          tags:
            - key: vendor
              value: ntust-taiwan-lab
            - key: sourceName
              field: event.commonEventHeader.sourceName
          fields:
            - key: avg-throughput-downlink
              field: event.stndDefinedFields.data.measurements[0].value
              type: int
            - key: ue-avg-mcs-index
              field: event.stndDefinedFields.data.measurements[1].value
              type: float
buckets:
  - name: my-bucket
```

:::

<br>

:::warning
:warning: **[Do Remember !](#-NOTE)**
:::

### Result 

![](https://hackmd.io/_uploads/HJn-pGEFh.png)




----

## Reporting PM on Grafana

- Explore and Run query
```bash=
## Example:
from(bucket: "my-bucket") 
  |> range(start: -10m)
```

### Result 
![](https://hackmd.io/_uploads/S1LVAMVYh.png)

![](https://hackmd.io/_uploads/B1U_6MVKn.png)


## Dashboards
- Administration > Data sources > InfluxDB > Build a dashboard > Add visualization
### Query 
```bash=
## Example:
from(bucket: "my-bucket")
  |> range(start: -10m)
  |> filter(fn: (r) => r._measurement == "slice-measurement" and r._field == "slice3_avgThroughputDownlink")
```

### Result
 
![](https://hackmd.io/_uploads/BkrtVXNK2.png)

## Netcof Client and Server 
**Client:** SMO
**Server:** O-DU

### 1. [Set up Netconf Server](https://hackmd.io/tmTNEE7ET4S8mt3G6wCJzA#2-Set-up-Netconf-Server)

:::info
**Configurations:**
1. local-address configuration:
    1. Open the netconf_server_ipv6.xml.
        ```shell
        # Move to config folder.
        cd <O-DU High Directory>/l2/build/config

        # Open the file using vim editor.
        vim netconf_server_ipv6.xml
        ```
    2. Modify the ip address in **line 7** (no need use local-address).
        ```xml=
        <netconf-server xmlns="urn:ietf:params:xml:ns:yang:ietf-netconf-server">
          <listen>
            <endpoint>
              <name>default-ssh</name>
              <ssh>
                <tcp-server-parameters>
                  <local-address>::</local-address>
        ```
<!-- 
Open the smoVesConfig.json, oanVesConfig.json and edit the details of VES collector.
```shell=
$ vim smoVesConfig.json
$ vim oamVesConfig.json 
``` -->

2. vesV4IpAddress configurations:
    **Folder**: `<O-DU High Directory>/l2/build/config`
    - smoVesConfig.json 
        ```json
        {
            "vesConfig": {
                "vesV4IpAddress" : "<smo ip>",
                "vesPort" : "30205",
                "username" : "user",
                "password" : "password"
            }
        }
        ```
    - oamVesConfig.json 
        ```json
        {
            "vesConfig": {
                "vesV4IpAddress" : "<smo ip>",
                "vesPort" : "30417",
                "username" : "sample1",
                "password" : "sample1"
            }
        }
        ```

3. Netconf configuration:
    **Folder**: `<O-DU High Directory>/l2/build/config`
    - netconfConfig.json<br>
    Edit the details of Netopeer server:
        - MacAddress
        - NetconfServerIpv4
        - NetconfServerIpv6
        ```json
        {
            "NetconfServer": {
                "MacAddress": "A4:Bf:01:75:23:B8",
                "NetconfServerIpv4": "192.168.8.5",
                "NetconfServerIpv6": "fd90:f942:f30c::141",
                "NetconfPort": "830",
                "NetconfUsername": "netconf",
                "NetconfPassword": "netconf!"
            }
        }
        ```
        > Keep in mind the username and password for later use cases.

:::

### 2. NetConf Client

>Install netopeer2 in SMO server

#### 2.1 Install the libssh

```bash=
wget https://git.libssh.org/projects/libssh.git/snapshot/libssh-0.9.5.tar.gz
tar -xf libssh-0.9.5.tar.gz
rm libssh-0.9.5.tar.gz
cd libssh-0.9.5
mkdir build && cd build
cmake ..
make
sudo make install
```
#### 2.2 Install the libyang
```bash=
sudo -i
git clone https://github.com/CESNET/libyang.git
cd libyang
mkdir build && cd build && cmake .. && make && make install
```


#### 2.3 Install the sysrepo
```bash=
cd ~
git clone https://github.com/sysrepo/sysrepo.git
cd sysrepo
mkdir build && cd build && cmake .. && make && make install
```

#### 2.4 Install the libnetconf2
```bash=
cd ~
git clone https://github.com/CESNET/libnetconf2.git
cd libnetconf2
mkdir build && cd build && cmake .. && make && make install
```

#### 2.5 Install the netopeer2
```bash=
cd ~
git clone https://github.com/CESNET/netopeer2.git
cd netopeer2
mkdir build && cd build && cmake .. && make && make install
```

#### 2.6 Test the O1-Netconf (O-DU IP here we use 192.168.8.112 )

- 2.6.1 Copy configuration file to SMO server
- 2.6.2 Use netopeer2-cli to connect O-DU 

**SMO :**
```bash=
netopeer2-cli
connect --host 192.168.8.112 --port 830 --login netconf
edit-config --target candidate --config=cellConfig.xml
commit
```

![image](https://hackmd.io/_uploads/BJTP16dW0.png)


----

## How O-DU wraps data into VES Agent to VES Collector

![](https://hackmd.io/_uploads/ryWa8YvHn.png)

:::warning
- `DuProcRlcSliceMetrics`
    - src/du_app
    - Handles received Slice Metrics **from RLC and forward it to O1**
- `sendSliceMetric`
    - src/o1/PmInterface.cpp
    - Takes the Slice metrics list and **sends it to SMO as a VES message**
- `VesEventHandler::send()`
    - Send VES event to SMO
- `HttpClient::send`
    - src/o1/ves
    - prepare curl header
    - sends VES event with help of curl API to VES collector
- `sendMsg()`
    - src/phy_stub
    - function build the message which need to send to target PHY 

:::