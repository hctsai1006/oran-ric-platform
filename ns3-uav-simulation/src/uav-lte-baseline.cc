/**
 * UAV LTE Baseline Simulation for xApp Validation
 *
 * This simulation creates a UAV flying over 3 LTE eNBs and records
 * radio metrics without any xApp control (baseline).
 *
 * Author: Research Team
 * Date: 2025-11-21
 * Purpose: Establish baseline for comparison with xApp-controlled scenario
 *
 * Network Topology:
 *   eNB#1 (200,200,30) ---- eNB#2 (500,500,30) ---- eNB#3 (800,200,30)
 *                   \          |          /
 *                    \         |         /
 *                     UAV flying path (100m altitude)
 *                    (100,100) --> (900,900)
 */

#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/internet-module.h"
#include "ns3/mobility-module.h"
#include "ns3/lte-module.h"
#include "ns3/point-to-point-module.h"
#include "ns3/applications-module.h"
#include "ns3/config-store-module.h"

#include <fstream>
#include <iomanip>
#include <ctime>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE("UavLteBaseline");

// Global variables for metrics collection
std::ofstream g_metricsFile;
std::ofstream g_handoverFile;
uint32_t g_handoverCount = 0;
Time g_lastHandoverTime = Seconds(0);

/**
 * Callback for RSRP/RSRQ measurements from PHY layer
 */
void ReportUeMeasurements(uint16_t rnti, uint16_t cellId,
                          double rsrp, double rsrq, bool isServingCell,
                          uint8_t componentCarrierId)
{
  double simTime = Simulator::Now().GetSeconds();

  std::string cellType = isServingCell ? "SERVING" : "NEIGHBOR";

  g_metricsFile << std::fixed << std::setprecision(3)
                << simTime << ","
                << rnti << ","
                << cellId << ","
                << cellType << ","
                << rsrp << ","
                << rsrq << std::endl;

  if (isServingCell) {
    NS_LOG_INFO("t=" << simTime << "s | RNTI=" << rnti
                << " | ServingCell=" << cellId
                << " | RSRP=" << rsrp << " dBm"
                << " | RSRQ=" << rsrq << " dB");
  }
}

/**
 * Callback for handover events
 */
void NotifyHandoverStart(std::string context, uint64_t imsi, uint16_t cellId,
                         uint16_t rnti, uint16_t targetCellId)
{
  double simTime = Simulator::Now().GetSeconds();

  NS_LOG_INFO("HANDOVER START: t=" << simTime << "s | IMSI=" << imsi
              << " | " << cellId << " -> " << targetCellId);

  g_handoverFile << std::fixed << std::setprecision(3)
                 << simTime << ",START," << imsi << ","
                 << cellId << "," << targetCellId << std::endl;
}

void NotifyHandoverEnd(std::string context, uint64_t imsi, uint16_t cellId, uint16_t rnti)
{
  double simTime = Simulator::Now().GetSeconds();

  g_handoverCount++;
  double handoverDelay = (simTime - g_lastHandoverTime.GetSeconds());
  g_lastHandoverTime = Simulator::Now();

  NS_LOG_INFO("HANDOVER END: t=" << simTime << "s | IMSI=" << imsi
              << " | NewCell=" << cellId << " | TotalHandovers=" << g_handoverCount);

  g_handoverFile << std::fixed << std::setprecision(3)
                 << simTime << ",END," << imsi << ","
                 << cellId << "," << g_handoverCount << std::endl;
}

/**
 * Position logging callback
 */
void LogUavPosition(Ptr<Node> uavNode)
{
  Ptr<MobilityModel> mobility = uavNode->GetObject<MobilityModel>();
  Vector pos = mobility->GetPosition();
  Vector vel = mobility->GetVelocity();

  double speed = std::sqrt(vel.x*vel.x + vel.y*vel.y + vel.z*vel.z);

  NS_LOG_INFO("UAV Position: (" << pos.x << ", " << pos.y << ", " << pos.z
              << ") | Speed: " << speed << " m/s");

  // Schedule next position log
  Simulator::Schedule(Seconds(1.0), &LogUavPosition, uavNode);
}

int main(int argc, char *argv[])
{
  // ========== Simulation Parameters ==========
  double simTime = 100.0;           // Total simulation time (seconds)
  double reportInterval = 0.5;      // RSRP reporting interval (seconds)
  uint16_t bandwidth = 100;         // PRBs (20 MHz)
  double enbTxPower = 46.0;         // eNB TX power (dBm)
  double ueTxPower = 23.0;          // UE TX power (dBm)
  std::string outputDir = "/home/thc1006/dev/oran-ric-platform/ns3-uav-simulation/results/baseline/";
  bool verbose = false;

  // ========== Command Line Arguments ==========
  CommandLine cmd;
  cmd.AddValue("simTime", "Simulation time in seconds", simTime);
  cmd.AddValue("reportInterval", "RSRP report interval", reportInterval);
  cmd.AddValue("outputDir", "Output directory for results", outputDir);
  cmd.AddValue("verbose", "Enable verbose logging", verbose);
  cmd.Parse(argc, argv);

  if (verbose) {
    LogComponentEnable("UavLteBaseline", LOG_LEVEL_INFO);
    LogComponentEnable("LteUeRrc", LOG_LEVEL_INFO);
  }

  // ========== Create Output Files ==========
  std::string timestamp = std::to_string(std::time(nullptr));
  g_metricsFile.open(outputDir + "metrics_" + timestamp + ".csv");
  g_handoverFile.open(outputDir + "handovers_" + timestamp + ".csv");

  g_metricsFile << "time,rnti,cellId,cellType,rsrp_dBm,rsrq_dB" << std::endl;
  g_handoverFile << "time,event,imsi,cellId,targetOrCount" << std::endl;

  NS_LOG_INFO("========================================");
  NS_LOG_INFO("UAV LTE Baseline Simulation");
  NS_LOG_INFO("========================================");
  NS_LOG_INFO("Simulation Time: " << simTime << " seconds");
  NS_LOG_INFO("Output Directory: " << outputDir);

  // ========== Create LTE Helper ==========
  Ptr<LteHelper> lteHelper = CreateObject<LteHelper>();
  Ptr<PointToPointEpcHelper> epcHelper = CreateObject<PointToPointEpcHelper>();
  lteHelper->SetEpcHelper(epcHelper);

  // Configure handover algorithm (A2-A4 RSRQ based)
  lteHelper->SetHandoverAlgorithmType("ns3::A2A4RsrqHandoverAlgorithm");
  lteHelper->SetHandoverAlgorithmAttribute("ServingCellThreshold", UintegerValue(30));
  lteHelper->SetHandoverAlgorithmAttribute("NeighbourCellOffset", UintegerValue(1));

  // Configure scheduler
  lteHelper->SetSchedulerType("ns3::PfFfMacScheduler");

  // Configure channel model (Urban Macro)
  lteHelper->SetAttribute("PathlossModel", StringValue("ns3::Cost231PropagationLossModel"));

  // ========== Create Nodes ==========
  NodeContainer enbNodes;
  enbNodes.Create(3);

  NodeContainer ueNodes;
  ueNodes.Create(1);  // Single UAV

  // ========== Configure Mobility ==========
  // eNB positions (fixed)
  MobilityHelper enbMobility;
  Ptr<ListPositionAllocator> enbPositionAlloc = CreateObject<ListPositionAllocator>();
  enbPositionAlloc->Add(Vector(200.0, 200.0, 30.0));   // eNB#1
  enbPositionAlloc->Add(Vector(500.0, 500.0, 30.0));   // eNB#2
  enbPositionAlloc->Add(Vector(800.0, 200.0, 30.0));   // eNB#3
  enbMobility.SetPositionAllocator(enbPositionAlloc);
  enbMobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
  enbMobility.Install(enbNodes);

  // UAV mobility (waypoint-based flight path)
  MobilityHelper uavMobility;
  uavMobility.SetMobilityModel("ns3::WaypointMobilityModel");
  uavMobility.Install(ueNodes);

  Ptr<WaypointMobilityModel> waypointMobility =
      ueNodes.Get(0)->GetObject<WaypointMobilityModel>();

  // Define UAV flight path (diagonal across the coverage area)
  // Speed: ~15 m/s (calculated from waypoint distances and times)
  waypointMobility->AddWaypoint(Waypoint(Seconds(0.0),  Vector(100.0, 100.0, 100.0)));   // Start
  waypointMobility->AddWaypoint(Waypoint(Seconds(20.0), Vector(300.0, 300.0, 100.0)));   // Near eNB#1
  waypointMobility->AddWaypoint(Waypoint(Seconds(40.0), Vector(500.0, 500.0, 100.0)));   // Near eNB#2
  waypointMobility->AddWaypoint(Waypoint(Seconds(60.0), Vector(700.0, 700.0, 100.0)));   // Between eNB#2,#3
  waypointMobility->AddWaypoint(Waypoint(Seconds(75.0), Vector(900.0, 900.0, 100.0)));   // End
  waypointMobility->AddWaypoint(Waypoint(Seconds(100.0), Vector(900.0, 900.0, 100.0)));  // Stay at end

  NS_LOG_INFO("UAV flight path configured: (100,100) -> (900,900) @ ~15 m/s");

  // ========== Install LTE Devices ==========
  // Configure eNB
  Config::SetDefault("ns3::LteEnbPhy::TxPower", DoubleValue(enbTxPower));
  Config::SetDefault("ns3::LteEnbNetDevice::DlBandwidth", UintegerValue(bandwidth));
  Config::SetDefault("ns3::LteEnbNetDevice::UlBandwidth", UintegerValue(bandwidth));

  NetDeviceContainer enbDevices = lteHelper->InstallEnbDevice(enbNodes);

  // Configure UE (UAV)
  Config::SetDefault("ns3::LteUePhy::TxPower", DoubleValue(ueTxPower));

  NetDeviceContainer ueDevices = lteHelper->InstallUeDevice(ueNodes);

  // ========== Install Internet Stack ==========
  InternetStackHelper internet;
  internet.Install(ueNodes);

  Ipv4InterfaceContainer ueIpInterfaces = epcHelper->AssignUeIpv4Address(ueDevices);

  // Set default gateway
  Ptr<Node> pgw = epcHelper->GetPgwNode();
  Ipv4StaticRoutingHelper ipv4RoutingHelper;
  Ptr<Ipv4StaticRouting> ueStaticRouting =
      ipv4RoutingHelper.GetStaticRouting(ueNodes.Get(0)->GetObject<Ipv4>());
  ueStaticRouting->SetDefaultRoute(epcHelper->GetUeDefaultGatewayAddress(), 1);

  // ========== Attach UE to Initial eNB ==========
  lteHelper->Attach(ueDevices.Get(0), enbDevices.Get(0));  // Start attached to eNB#1

  // ========== Configure X2 for Handover ==========
  lteHelper->AddX2Interface(enbNodes);

  // ========== Install Applications (Video Upload Simulation) ==========
  uint16_t dlPort = 10000;
  uint16_t ulPort = 20000;

  // Uplink: UAV video streaming to remote server (25 Mbps)
  OnOffHelper ulClient("ns3::UdpSocketFactory",
                       InetSocketAddress(pgw->GetObject<Ipv4>()->GetAddress(1,0).GetLocal(), ulPort));
  ulClient.SetAttribute("DataRate", DataRateValue(DataRate("25Mbps")));
  ulClient.SetAttribute("PacketSize", UintegerValue(1400));
  ulClient.SetAttribute("OnTime", StringValue("ns3::ConstantRandomVariable[Constant=1]"));
  ulClient.SetAttribute("OffTime", StringValue("ns3::ConstantRandomVariable[Constant=0]"));

  ApplicationContainer ulClientApp = ulClient.Install(ueNodes.Get(0));
  ulClientApp.Start(Seconds(1.0));
  ulClientApp.Stop(Seconds(simTime - 1.0));

  // Uplink sink
  PacketSinkHelper ulSink("ns3::UdpSocketFactory",
                          InetSocketAddress(Ipv4Address::GetAny(), ulPort));
  ApplicationContainer ulSinkApp = ulSink.Install(pgw);
  ulSinkApp.Start(Seconds(0.5));
  ulSinkApp.Stop(Seconds(simTime));

  // ========== Configure Measurement Reporting ==========
  Config::SetDefault("ns3::LteUePhy::RsrpSinrSamplePeriod", UintegerValue(50));  // 50ms

  // Connect to RRC measurement reports
  Config::Connect("/NodeList/*/DeviceList/*/LteUePhy/ReportUeMeasurements",
                  MakeCallback(&ReportUeMeasurements));

  // Connect to handover events
  Config::Connect("/NodeList/*/DeviceList/*/LteUeRrc/HandoverStart",
                  MakeCallback(&NotifyHandoverStart));
  Config::Connect("/NodeList/*/DeviceList/*/LteUeRrc/HandoverEndOk",
                  MakeCallback(&NotifyHandoverEnd));

  // ========== Schedule Position Logging ==========
  Simulator::Schedule(Seconds(1.0), &LogUavPosition, ueNodes.Get(0));

  // ========== Enable Tracing ==========
  lteHelper->EnablePhyTraces();
  lteHelper->EnableMacTraces();
  lteHelper->EnableRlcTraces();
  lteHelper->EnablePdcpTraces();

  // ========== Run Simulation ==========
  NS_LOG_INFO("Starting simulation...");

  Simulator::Stop(Seconds(simTime));
  Simulator::Run();

  // ========== Collect Final Statistics ==========
  NS_LOG_INFO("========================================");
  NS_LOG_INFO("Simulation Complete");
  NS_LOG_INFO("========================================");
  NS_LOG_INFO("Total Handovers: " << g_handoverCount);

  // Write summary
  std::ofstream summaryFile(outputDir + "summary_" + timestamp + ".txt");
  summaryFile << "UAV LTE Baseline Simulation Summary" << std::endl;
  summaryFile << "====================================" << std::endl;
  summaryFile << "Simulation Time: " << simTime << " s" << std::endl;
  summaryFile << "Total Handovers: " << g_handoverCount << std::endl;
  summaryFile << "eNB Configuration:" << std::endl;
  summaryFile << "  - eNB#1: (200, 200, 30)" << std::endl;
  summaryFile << "  - eNB#2: (500, 500, 30)" << std::endl;
  summaryFile << "  - eNB#3: (800, 200, 30)" << std::endl;
  summaryFile << "UAV Configuration:" << std::endl;
  summaryFile << "  - Altitude: 100 m" << std::endl;
  summaryFile << "  - Speed: ~15 m/s" << std::endl;
  summaryFile << "  - Path: (100,100) -> (900,900)" << std::endl;
  summaryFile.close();

  g_metricsFile.close();
  g_handoverFile.close();

  Simulator::Destroy();

  return 0;
}
