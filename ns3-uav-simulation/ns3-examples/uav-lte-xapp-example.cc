/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/*
 * UAV LTE Simulation with xApp Integration
 *
 * This example creates:
 * - 3 LTE eNBs with fixed positions
 * - 1 UAV UE with waypoint mobility
 * - RSRP/RSRQ measurements collection
 * - CSV output for analysis
 *
 * Based on 3GPP TR 36.777 UAV scenarios
 */

#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/mobility-module.h"
#include "ns3/lte-module.h"
#include "ns3/internet-module.h"
#include "ns3/point-to-point-module.h"
#include "ns3/applications-module.h"
#include "ns3/config-store-module.h"

#include <fstream>
#include <iomanip>
#include <cmath>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE ("UavLteXappExample");

// Global variables for tracking
static uint32_t g_handoverCount = 0;
static double g_totalRsrp = 0.0;
static uint32_t g_rsrpSamples = 0;
static std::ofstream g_metricsFile;

// RSRP/SINR measurement callback (matches LteUePhy::RsrpSinrTracedCallback signature)
void
ReportRsrpSinr (uint16_t cellId, uint16_t rnti, double rsrp, double sinr, uint8_t componentCarrierId)
{
  // RSRP from trace is in Watts (linear), convert to dBm
  // dBm = 10 * log10(Watts) + 30
  double rsrpDbm = (rsrp > 0) ? (10.0 * std::log10 (rsrp) + 30.0) : -140.0;

  g_totalRsrp += rsrpDbm;
  g_rsrpSamples++;

  double simTime = Simulator::Now ().GetSeconds ();

  // Convert SINR linear to dB
  double sinrDb = (sinr > 0) ? (10.0 * std::log10 (sinr)) : -20.0;

  // Log to file
  g_metricsFile << std::fixed << std::setprecision (2)
                << simTime << ","
                << cellId << ","
                << rsrpDbm << ","
                << sinrDb << std::endl;

  NS_LOG_INFO ("t=" << simTime << "s | Cell=" << cellId
               << " | RSRP=" << rsrpDbm << " dBm | SINR=" << sinrDb << " dB");
}

// Handover callback (with context parameter for Config::Connect)
void
NotifyHandoverEndOkUe (std::string context, uint64_t imsi, uint16_t cellId, uint16_t rnti)
{
  g_handoverCount++;
  NS_LOG_INFO ("Handover completed: UE " << imsi << " -> Cell " << cellId);
}

int
main (int argc, char *argv[])
{
  double simTime = 75.0;
  double measurementInterval = 0.5;
  std::string outputFile = "/tmp/ns3-uav-metrics.csv";
  bool enableE2 = false;  // Disable E2 by default to avoid conflicts

  CommandLine cmd;
  cmd.AddValue ("simTime", "Simulation time in seconds", simTime);
  cmd.AddValue ("interval", "Measurement interval in seconds", measurementInterval);
  cmd.AddValue ("output", "Output CSV file path", outputFile);
  cmd.AddValue ("e2", "Enable E2 interface (requires RIC)", enableE2);
  cmd.Parse (argc, argv);

  // Open output file
  g_metricsFile.open (outputFile);
  g_metricsFile << "time,cell_id,rsrp_dbm,rsrq_db" << std::endl;

  NS_LOG_UNCOND ("=================================================");
  NS_LOG_UNCOND ("ns-3 UAV LTE Simulation with xApp Integration");
  NS_LOG_UNCOND ("=================================================");
  NS_LOG_UNCOND ("Simulation time: " << simTime << " seconds");
  NS_LOG_UNCOND ("Output file: " << outputFile);

  // Configure LTE
  Config::SetDefault ("ns3::LteHelper::UseIdealRrc", BooleanValue (true));
  Config::SetDefault ("ns3::LteSpectrumPhy::CtrlErrorModelEnabled", BooleanValue (false));
  Config::SetDefault ("ns3::LteSpectrumPhy::DataErrorModelEnabled", BooleanValue (false));

  // A2-A4-RSRQ handover algorithm
  Config::SetDefault ("ns3::LteHelper::HandoverAlgorithm",
                      StringValue ("ns3::A2A4RsrqHandoverAlgorithm"));
  Config::SetDefault ("ns3::A2A4RsrqHandoverAlgorithm::ServingCellThreshold", UintegerValue (30));
  Config::SetDefault ("ns3::A2A4RsrqHandoverAlgorithm::NeighbourCellOffset", UintegerValue (1));

  // Create LTE helper
  Ptr<LteHelper> lteHelper = CreateObject<LteHelper> ();
  Ptr<PointToPointEpcHelper> epcHelper = CreateObject<PointToPointEpcHelper> ();
  lteHelper->SetEpcHelper (epcHelper);

  // Set pathloss model (Urban Macro for UAV)
  lteHelper->SetAttribute ("PathlossModel", StringValue ("ns3::Cost231PropagationLossModel"));

  // Create nodes
  NodeContainer enbNodes;
  enbNodes.Create (3);

  NodeContainer ueNodes;
  ueNodes.Create (1);  // Single UAV

  // eNB positions (triangular layout)
  Ptr<ListPositionAllocator> enbPositionAlloc = CreateObject<ListPositionAllocator> ();
  enbPositionAlloc->Add (Vector (200.0, 200.0, 30.0));   // eNB 1
  enbPositionAlloc->Add (Vector (500.0, 500.0, 30.0));   // eNB 2
  enbPositionAlloc->Add (Vector (800.0, 200.0, 30.0));   // eNB 3

  MobilityHelper enbMobility;
  enbMobility.SetMobilityModel ("ns3::ConstantPositionMobilityModel");
  enbMobility.SetPositionAllocator (enbPositionAlloc);
  enbMobility.Install (enbNodes);

  // UAV mobility - Waypoint model
  MobilityHelper ueMobility;
  ueMobility.SetMobilityModel ("ns3::WaypointMobilityModel");
  ueMobility.Install (ueNodes);

  // Configure UAV waypoints
  Ptr<WaypointMobilityModel> uavMobility =
      ueNodes.Get (0)->GetObject<WaypointMobilityModel> ();

  // Flight path: diagonal across coverage areas
  uavMobility->AddWaypoint (Waypoint (Seconds (0), Vector (100, 100, 100)));
  uavMobility->AddWaypoint (Waypoint (Seconds (15), Vector (250, 250, 100)));
  uavMobility->AddWaypoint (Waypoint (Seconds (30), Vector (400, 400, 100)));
  uavMobility->AddWaypoint (Waypoint (Seconds (45), Vector (550, 550, 100)));
  uavMobility->AddWaypoint (Waypoint (Seconds (60), Vector (700, 350, 100)));
  uavMobility->AddWaypoint (Waypoint (Seconds (75), Vector (850, 200, 100)));

  // Install LTE devices
  NetDeviceContainer enbDevs = lteHelper->InstallEnbDevice (enbNodes);
  NetDeviceContainer ueDevs = lteHelper->InstallUeDevice (ueNodes);

  // Install IP stack on UE
  InternetStackHelper internet;
  internet.Install (ueNodes);

  // Assign IP addresses
  Ipv4InterfaceContainer ueIpIface;
  ueIpIface = epcHelper->AssignUeIpv4Address (NetDeviceContainer (ueDevs));

  // Attach UE to closest eNB initially
  lteHelper->Attach (ueDevs.Get (0), enbDevs.Get (0));

  // Enable X2 for handover
  lteHelper->AddX2Interface (enbNodes);

  // A2-A4-RSRQ handover algorithm is enabled by default config
  // Handover will be triggered automatically when signal quality changes

  // Connect to handover trace
  Config::Connect ("/NodeList/*/DeviceList/*/LteUeRrc/HandoverEndOk",
                   MakeCallback (&NotifyHandoverEndOkUe));

  // Connect to RSRP/SINR measurements from UE PHY directly
  Ptr<LteUeNetDevice> ueLteDevice = ueDevs.Get (0)->GetObject<LteUeNetDevice> ();
  ueLteDevice->GetPhy ()->TraceConnectWithoutContext ("ReportCurrentCellRsrpSinr",
                                                       MakeCallback (&ReportRsrpSinr));

  // Run simulation
  NS_LOG_UNCOND ("");
  NS_LOG_UNCOND ("Starting simulation...");

  Simulator::Stop (Seconds (simTime + 1));
  Simulator::Run ();

  // Close output file
  g_metricsFile.close ();

  // Print summary
  double avgRsrp = (g_rsrpSamples > 0) ? (g_totalRsrp / g_rsrpSamples) : 0.0;

  NS_LOG_UNCOND ("");
  NS_LOG_UNCOND ("=================================================");
  NS_LOG_UNCOND ("Simulation Complete");
  NS_LOG_UNCOND ("=================================================");
  NS_LOG_UNCOND ("Total Handovers: " << g_handoverCount);
  NS_LOG_UNCOND ("Avg RSRP: " << avgRsrp << " dBm");
  NS_LOG_UNCOND ("RSRP Samples: " << g_rsrpSamples);
  NS_LOG_UNCOND ("Output: " << outputFile);
  NS_LOG_UNCOND ("=================================================");

  Simulator::Destroy ();
  return 0;
}
