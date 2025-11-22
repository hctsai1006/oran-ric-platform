# E2 Interface Integration Design

## Overview

This document describes the integration design for connecting ns-3 UAV simulation with O-RAN Near-RT RIC via the E2 interface. The design leverages the ns-O-RAN module (`/opt/ns-oran/contrib/oran/`) which provides E2AP protocol implementation compatible with OSC RIC.

---

## 1. E2AP Protocol Architecture

### 1.1 E2 Interface Stack

```
+------------------+     +------------------+
|   UAV xApp       |     |   KPM xApp       |
|  (Policy Engine) |     |  (Monitoring)    |
+--------+---------+     +--------+---------+
         |                        |
         v                        v
+------------------------------------------------+
|              Near-RT RIC Platform              |
|  +------------------------------------------+  |
|  |          E2 Termination (E2T)            |  |
|  +------------------------------------------+  |
+------------------------+------------------------+
                         |
                    E2AP (SCTP)
                         |
+------------------------v------------------------+
|              ns-3 E2 Termination               |
|  +------------------------------------------+  |
|  |   E2Sim Library (o-ran-e2sim)            |  |
|  +------------------------------------------+  |
|  +------------------------------------------+  |
|  |   KPM Indication + RC Control Service    |  |
|  +------------------------------------------+  |
+------------------------------------------------+
|              ns-3 LTE/NR Simulation            |
|       (eNB, UE, Channel, Mobility Models)      |
+------------------------------------------------+
```

### 1.2 E2AP Message Types

| Message Type | Direction | Description |
|--------------|-----------|-------------|
| E2 Setup Request | E2 Node -> RIC | Initialize E2 connection, register RAN functions |
| E2 Setup Response | RIC -> E2 Node | Acknowledge E2 setup |
| RIC Subscription Request | RIC -> E2 Node | xApp subscribes to KPM reports |
| RIC Subscription Response | E2 Node -> RIC | Acknowledge subscription |
| RIC Indication | E2 Node -> RIC | Periodic/triggered KPM reports |
| RIC Control Request | RIC -> E2 Node | xApp sends control commands |
| RIC Control Acknowledge | E2 Node -> RIC | Acknowledge control execution |

---

## 2. E2AP Message Formats

### 2.1 E2 Setup Request

```asn1
E2setupRequest ::= SEQUENCE {
    protocolIEs  ProtocolIE-Container {
        -- Global E2 Node ID
        id-GlobalE2node-ID    GlobalE2node-ID,
        -- RAN Functions Added List
        id-RANfunctionsAdded  RANfunctions-List OPTIONAL
    }
}

GlobalE2node-ID ::= CHOICE {
    gNB     GlobalE2node-gNB-ID,
    en-gNB  GlobalE2node-en-gNB-ID,
    ng-eNB  GlobalE2node-ng-eNB-ID,
    eNB     GlobalE2node-eNB-ID
}
```

**ns-O-RAN Implementation:**
```cpp
// From oran-interface.cc
E2Termination::E2Termination(
    const std::string ricAddress,    // RIC IP address
    const uint16_t ricPort,          // RIC SCTP port (36422)
    const uint16_t clientPort,       // Local bind port
    const std::string gnbId,         // 4-byte gNB ID
    const std::string plmnId)        // 3-byte PLMN ID
```

### 2.2 RIC Subscription Request/Response

```asn1
RICsubscriptionRequest ::= SEQUENCE {
    protocolIEs  ProtocolIE-Container {
        id-RICrequestID           RICrequestID,
        id-RANfunctionID          RANfunctionID,
        id-RICsubscriptionDetails RICsubscriptionDetails
    }
}

RICsubscriptionDetails ::= SEQUENCE {
    ricEventTriggerDefinition  RICeventTriggerDefinition,
    ricAction-ToBeSetup-List   RICactions-ToBeSetup-List
}
```

**ns-O-RAN Implementation:**
```cpp
// From oran-interface.cc
E2Termination::RicSubscriptionRequest_rval_s
E2Termination::ProcessRicSubscriptionRequest(E2AP_PDU_t* sub_req_pdu) {
    // Returns:
    // - requestorId: RIC Requestor ID
    // - instanceId:  RIC Instance ID
    // - ranFuncionId: RAN Function ID (KPM=2, RC=3)
    // - actionId:    RIC Action ID
}
```

### 2.3 E2SM-KPM Indication Header

```asn1
E2SM-KPM-IndicationHeader-Format1 ::= SEQUENCE {
    id-GlobalE2node-ID   GlobalE2node-ID,
    collectionStartTime  TimeStamp    -- 8-byte timestamp
}
```

**ns-O-RAN Data Structure:**
```cpp
// From kpm-indication.h
struct KpmRicIndicationHeaderValues {
    std::string m_gnbId;      // gNB ID bit string (4 bytes for gNB)
    uint16_t m_nrCellId;      // NR Cell ID
    std::string m_plmId;      // PLMN identity (3 bytes)
    uint64_t m_timestamp;     // Collection timestamp
};
```

### 2.4 E2SM-KPM Indication Message

```asn1
E2SM-KPM-IndicationMessage-Format1 ::= SEQUENCE {
    pm-Containers            PM-Containers-List,
    cellObjectID             CellObjectID,
    list-of-PM-Information   MeasurementInfoList OPTIONAL,
    list-of-matched-UEs      UE-Info-List OPTIONAL
}
```

**ns-O-RAN Data Structure:**
```cpp
// From kpm-indication.h
struct KpmIndicationMessageValues {
    std::string m_cellObjectId;
    Ptr<PmContainerValues> m_pmContainerValues;
    Ptr<MeasurementItemList> m_cellMeasurementItems;
    std::set<Ptr<MeasurementItemList>> m_ueIndications;
};

// PM Container Types
class OCuCpContainerValues : public PmContainerValues {
    uint16_t m_numActiveUes;  // Number of active UEs
};

class OCuUpContainerValues : public PmContainerValues {
    std::string m_plmId;
    long m_pDCPBytesUL;       // Total PDCP bytes UL
    long m_pDCPBytesDL;       // Total PDCP bytes DL
};

class ODuContainerValues : public PmContainerValues {
    std::set<Ptr<CellResourceReport>> m_cellResourceReportItems;
};
```

### 2.5 E2SM-RC Control Message

```asn1
E2SM-RC-ControlHeader-Format1 ::= SEQUENCE {
    ueId                   UE-Identity,
    ric-ControlStyle-Type  RIC-Style-Type,
    ric-ControlAction-ID   RIC-Control-Action-ID
}

E2SM-RC-ControlMessage-Format1 ::= SEQUENCE {
    ranParameters-List     SEQUENCE OF RANParameter-Item
}
```

**ns-O-RAN Data Structure:**
```cpp
// From ric-control-message.h
class RicControlMessage {
    enum ControlMessageRequestIdType {
        TS = 1001,   // Traffic Steering
        QoS = 1002   // QoS Control
    };

    std::vector<RANParameterItem> m_valuesExtracted;
    RANfunctionID_t m_ranFunctionId;
    RICrequestID_t m_ricRequestId;
};
```

---

## 3. RIC Indication Flow

### 3.1 KPM Indication Workflow

```
ns-3 Simulation                  E2 Termination                Near-RT RIC
     |                                |                            |
     |  1. Radio Metrics Available    |                            |
     |------------------------------->|                            |
     |                                |                            |
     |  2. Create KPM Indication      |                            |
     |  - Header (gNB ID, timestamp)  |                            |
     |  - Message (PM containers)     |                            |
     |                                |                            |
     |                                | 3. Encode & Send           |
     |                                |--------------------------->|
     |                                |    E2AP RICindication      |
     |                                |                            |
     |                                |                     4. xApp Processing
     |                                |                     (Policy Decision)
     |                                |                            |
```

### 3.2 Indication Message Building

```cpp
// Step 1: Create Header
KpmIndicationHeader::KpmRicIndicationHeaderValues headerValues;
headerValues.m_gnbId = "gnbd";      // 4-byte gNB ID
headerValues.m_plmId = "111";       // MCC=001, MNC=01
headerValues.m_nrCellId = cellId;
headerValues.m_timestamp = std::time(nullptr);

Ptr<KpmIndicationHeader> header = Create<KpmIndicationHeader>(
    KpmIndicationHeader::GlobalE2nodeType::eNB, headerValues);

// Step 2: Create Message
KpmIndicationMessage::KpmIndicationMessageValues msgValues;
msgValues.m_cellObjectId = "NR_Cell_1";

// Add O-DU Container (PRB utilization)
Ptr<ODuContainerValues> duValues = Create<ODuContainerValues>();
Ptr<CellResourceReport> cellReport = Create<CellResourceReport>();
cellReport->m_plmId = "111";
cellReport->m_nrCellId = 1;
cellReport->dlAvailablePrbs = 100;
cellReport->ulAvailablePrbs = 100;
duValues->m_cellResourceReportItems.insert(cellReport);
msgValues.m_pmContainerValues = duValues;

// Add UE-specific measurements
Ptr<MeasurementItemList> ueMeasurements = Create<MeasurementItemList>("UAV-001");
ueMeasurements->AddItem<double>("RSRP", rsrpDbm);
ueMeasurements->AddItem<double>("SINR", sinrDb);
msgValues.m_ueIndications.insert(ueMeasurements);

Ptr<KpmIndicationMessage> message = Create<KpmIndicationMessage>(msgValues);

// Step 3: Send via E2AP
e2term->SendE2Message(indicationPdu);
```

---

## 4. RIC Control Flow

### 4.1 Control Message Workflow

```
Near-RT RIC                    E2 Termination                 ns-3 Simulation
     |                               |                              |
     | 1. xApp Decision              |                              |
     | (Handover/PRB allocation)     |                              |
     |                               |                              |
     | 2. E2AP RICcontrolRequest     |                              |
     |------------------------------>|                              |
     |                               |                              |
     |                               | 3. Decode Control Message    |
     |                               |   - Extract RAN Parameters   |
     |                               |   - Identify control type    |
     |                               |                              |
     |                               | 4. Apply Control Action      |
     |                               |----------------------------->|
     |                               |                              |
     |                               |         5. Execute           |
     |                               |      (Handover/PRB Update)   |
     |                               |                              |
     |   6. RICcontrolAck            |                              |
     |<------------------------------|                              |
```

### 4.2 Control Message Processing

```cpp
// Register SM callback for RC (RAN Control)
void RcControlCallback(E2AP_PDU_t* pdu) {
    Ptr<RicControlMessage> controlMsg = Create<RicControlMessage>(pdu);

    switch (controlMsg->m_requestType) {
        case RicControlMessage::TS: {
            // Traffic Steering - Handover
            std::string targetCellId = controlMsg->GetSecondaryCellIdHO();
            TriggerHandover(ueImsi, targetCellId);
            break;
        }
        case RicControlMessage::QoS: {
            // QoS Control - PRB Allocation
            for (auto& param : controlMsg->m_valuesExtracted) {
                if (param.m_name == "PRB_Quota") {
                    UpdatePrbAllocation(param.m_valueInt);
                }
            }
            break;
        }
    }
}
```

---

## 5. HTTP API to E2AP Mapping

### 5.1 Current HTTP API Endpoints

| HTTP Endpoint | HTTP Method | Description |
|---------------|-------------|-------------|
| `/e2/indication` | POST | Send radio metrics |
| `/api/v1/kpm/indication` | POST | KPM indication alternative |
| `/health` | GET | Health check |

### 5.2 HTTP to E2AP Message Mapping

| HTTP Field | E2SM-KPM Field | ASN.1 Type |
|------------|----------------|------------|
| `uav_id` | `ueId` in PerUE-PM-Item | OCTET STRING |
| `position.x/y/z` | Custom MeasurementItem | REAL |
| `serving_cell_id` | `cellObjectID` | PrintableString |
| `rsrp_serving` | MeasurementItem "RSRP" | REAL |
| `rsrq_serving` | MeasurementItem "RSRQ" | REAL |
| `prb_utilization_serving` | `dl_PRBUsage` in ODU | INTEGER (0..100) |
| `neighbor_cell_ids` | Additional CellResourceReport | SEQUENCE |
| `timestamp` | `collectionStartTime` | TimeStamp (8 bytes) |

### 5.3 E2AP to HTTP Response Mapping

| E2SM-RC Field | HTTP Response Field | Description |
|---------------|---------------------|-------------|
| `ric-ControlAction-ID` | `action` | "handover" or "prb_update" |
| RANParameter "Target-Cell-ID" | `target_cell_id` | Handover target |
| RANParameter "PRB-Quota" | `prb_quota` | Allocated PRBs |
| `RICrequestID` | `request_id` | Correlation ID |

---

## 6. ns-3 E2 Configuration

### 6.1 E2 Termination Setup

```cpp
// In ns-3 simulation main()
#include "ns3/oran-interface.h"

int main(int argc, char *argv[]) {
    // ... LTE/NR setup ...

    // Create E2 Termination for each eNB
    for (uint32_t i = 0; i < enbNodes.GetN(); i++) {
        std::string gnbId = "gnb" + std::to_string(i);

        Ptr<E2Termination> e2term = CreateObject<E2Termination>(
            "10.0.2.10",      // RIC IP address
            36422,            // RIC SCTP port
            38470 + i,        // Client port (unique per eNB)
            gnbId,            // gNB ID
            "111"             // PLMN ID
        );

        // Register KPM Service Model
        Ptr<KpmFunctionDescription> kpmFd = Create<KpmFunctionDescription>();
        e2term->RegisterKpmCallbackToE2Sm(
            2,                // RAN Function ID for KPM
            kpmFd,
            KpmSubscriptionCallback
        );

        // Register RC Service Model
        Ptr<RicControlFunctionDescription> rcFd = Create<RicControlFunctionDescription>();
        e2term->RegisterSmCallbackToE2Sm(
            3,                // RAN Function ID for RC
            rcFd,
            RcControlCallback
        );

        // Start E2 connection
        e2term->Start();
    }
}
```

### 6.2 KPM Subscription Callback

```cpp
void KpmSubscriptionCallback(E2AP_PDU_t* sub_req_pdu) {
    auto params = e2term->ProcessRicSubscriptionRequest(sub_req_pdu);

    // Store subscription info
    g_kpmSubscriptions[params.ranFuncionId] = {
        .requestorId = params.requestorId,
        .instanceId = params.instanceId,
        .actionId = params.actionId,
        .reportingPeriodMs = 1000  // Default 1 second
    };

    // Schedule periodic reporting
    Simulator::Schedule(
        MilliSeconds(g_kpmSubscriptions[params.ranFuncionId].reportingPeriodMs),
        &SendKpmIndication,
        params.ranFuncionId
    );
}
```

---

## 7. UAV-Specific E2 Extensions

### 7.1 Custom KPM Measurements for UAV

```cpp
// UAV-specific measurement items
Ptr<MeasurementItemList> uavMeasurements = Create<MeasurementItemList>("UAV-001");

// Standard LTE metrics
uavMeasurements->AddItem<double>("DRB.UEThpDl", throughputDl);
uavMeasurements->AddItem<double>("DRB.UEThpUl", throughputUl);
uavMeasurements->AddItem<double>("RRU.PrbUsedDl", prbUsedDl);
uavMeasurements->AddItem<double>("RRU.PrbUsedUl", prbUsedUl);

// UAV-specific metrics (custom)
uavMeasurements->AddItem<double>("UAV.RSRP.Serving", rsrpServing);
uavMeasurements->AddItem<double>("UAV.RSRP.Neighbor1", rsrpNeighbor1);
uavMeasurements->AddItem<double>("UAV.RSRP.Neighbor2", rsrpNeighbor2);
uavMeasurements->AddItem<double>("UAV.Position.X", positionX);
uavMeasurements->AddItem<double>("UAV.Position.Y", positionY);
uavMeasurements->AddItem<double>("UAV.Position.Z", altitude);
uavMeasurements->AddItem<double>("UAV.Velocity.Horizontal", velocityH);
uavMeasurements->AddItem<double>("UAV.Velocity.Vertical", velocityV);
uavMeasurements->AddItem<double>("UAV.PathProgress", pathProgress);
```

### 7.2 Custom RC Control Actions for UAV

```cpp
// Custom control actions
enum UavControlAction {
    UAV_HANDOVER = 1,           // Trigger handover
    UAV_PRB_ALLOCATION = 2,     // Adjust PRB quota
    UAV_SLICE_ASSIGNMENT = 3,   // Change network slice
    UAV_QOS_UPDATE = 4          // Update QoS parameters
};
```

---

## 8. Integration with OSC RIC

### 8.1 Required OSC RIC Components

| Component | Version | Purpose |
|-----------|---------|---------|
| E2 Termination (e2term) | >=3.0 | E2AP message handling |
| Subscription Manager | >=1.2 | xApp subscription management |
| Routing Manager | >=0.9 | Message routing |
| xApp Framework (Python) | >=1.4 | xApp SDK |

### 8.2 xApp Integration Points

```python
# Python xApp using OSC xApp Framework
from ricxappframe.xapp_frame import RMRXapp

class UavPolicyXapp(RMRXapp):
    def __init__(self):
        super().__init__(
            default_handler=self._default_handler,
            rmr_port=4560,
            use_fake_sdl=False
        )

        # Register handlers
        self.register_callback(
            self._kpm_indication_handler,
            RIC_INDICATION  # Message type 12050
        )

    def _kpm_indication_handler(self, summary, sbuf):
        # Decode E2SM-KPM indication
        indication = decode_e2sm_kpm(sbuf)

        # Extract UAV metrics
        uav_metrics = extract_uav_metrics(indication)

        # Make policy decision
        decision = self.policy_engine.evaluate(uav_metrics)

        # Send control if needed
        if decision.action != "maintain":
            self.send_control_request(decision)
```

---

## 9. Deployment Architecture

### 9.1 Development Environment

```
+-----------------------------------------+
|           Development Host              |
|  +-----------------------------------+  |
|  |    ns-3 + ns-O-RAN Module         |  |
|  |    (UAV LTE Simulation)           |  |
|  +----------------+------------------+  |
|                   | SCTP:36422          |
|  +----------------v------------------+  |
|  |    OSC RIC (Docker/K8s)           |  |
|  |    - e2term                       |  |
|  |    - e2mgr                        |  |
|  |    - submgr                       |  |
|  +----------------+------------------+  |
|                   | RMR               |
|  +----------------v------------------+  |
|  |    UAV Policy xApp                |  |
|  +-----------------------------------+  |
+-----------------------------------------+
```

### 9.2 Production Environment

```
+------------------+    +------------------+    +------------------+
|   Edge Site 1    |    |   Edge Site 2    |    |   Central RIC    |
|  +------------+  |    |  +------------+  |    |  +------------+  |
|  | ns-3 E2    |  |    |  | ns-3 E2    |  |    |  | OSC RIC    |  |
|  | Termination|  |    |  | Termination|  |    |  | Platform   |  |
|  +-----+------+  |    |  +-----+------+  |    |  +-----+------+  |
|        |         |    |        |         |    |        |         |
+--------|----------    +--------|----------    +--------|----------
         |                       |                       |
         +-----------------------+-----------------------+
                          E2AP over SCTP
```

---

## 10. Testing Strategy

### 10.1 Unit Tests

1. **E2AP Encoding/Decoding**: Verify ASN.1 message serialization
2. **KPM Indication Building**: Test PM container population
3. **RC Control Parsing**: Validate control message extraction

### 10.2 Integration Tests

1. **E2 Setup Flow**: Verify E2 connection establishment
2. **Subscription Flow**: Test KPM subscription and reporting
3. **Control Flow**: Validate control message round-trip

### 10.3 End-to-End Tests

1. **UAV Handover Scenario**: Verify xApp-triggered handover
2. **PRB Allocation Scenario**: Test dynamic resource allocation
3. **Multi-eNB Scenario**: Validate multi-cell coordination

---

## References

1. O-RAN.WG3.E2AP-v02.03: E2 Application Protocol
2. O-RAN.WG3.E2SM-KPM-v02.02: E2 Service Model for KPM
3. O-RAN.WG3.E2SM-RC-v01.03: E2 Service Model for RAN Control
4. ns-O-RAN GitHub: https://github.com/wineslab/ns-o-ran-e2
5. OSC RIC Documentation: https://wiki.o-ran-sc.org/
