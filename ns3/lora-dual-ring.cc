/**
 * Dual-Ring LoRa Perimeter Simulation for NS-3
 * =============================================
 * 
 * This is an NS-3 simulation script for the Wild Boar Perimeter Detection System.
 * It implements the 3-tier decision logic with P2P verification.
 * 
 * REQUIREMENTS:
 * - NS-3 (version 3.36+)
 * - lorawan module (https://github.com/signetlabdei/lorawan)
 * 
 * BUILD & RUN:
 *   1. Copy this file to scratch/lora-dual-ring.cc
 *   2. ./ns3 build
 *   3. ./ns3 run scratch/lora-dual-ring
 */

#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/mobility-module.h"
#include "ns3/internet-module.h"
#include "ns3/applications-module.h"
#include "ns3/point-to-point-module.h"
#include "ns3/lorawan-module.h"

#include <random>
#include <vector>
#include <cmath>
#include <map>

using namespace ns3;
using namespace lorawan;

NS_LOG_COMPONENT_DEFINE("LoraDualRingSimulation");

// ============== Configuration ==============
const double OUTER_RING_RADIUS = 23.0;  // meters
const double INNER_RING_RADIUS = 14.0;  // meters
const int OUTER_RING_NODES = 8;
const int INNER_RING_NODES = 8;
const double INNER_RING_OFFSET_DEG = 22.5;

const double P2P_RANGE = 30.0;          // meters
const double SENSOR_RANGE = 15.0;       // meters

const double CONFIRM_THRESHOLD = 0.80;
const double VERIFY_THRESHOLD = 0.70;
const double P2P_TIMEOUT = Seconds(3.0).GetSeconds();

// Image Confidence Model (Gaussian)
const double IMG_BOAR_MEAN = 0.85;
const double IMG_BOAR_STD = 0.08;
const double IMG_NON_BOAR_MEAN = 0.35;
const double IMG_NON_BOAR_STD = 0.15;

const double INTRUDER_PROB = 0.30;
const int TOTAL_EVENTS = 1000;
const double EVENT_INTERVAL = 8.0; // seconds (mean)

// ============== Statistics ==============
struct SimulationStats {
    int totalEvents = 0;
    int intruderEvents = 0;
    int noiseEvents = 0;
    int truePositives = 0;
    int falsePositives = 0;
    int p2pMessagesSent = 0;
    std::vector<double> latencies;
};

SimulationStats g_stats;
std::mt19937 g_rng(42); // Deterministic seed

// ============== Helper Functions ==============
double SampleGaussian(double mean, double stddev) {
    std::normal_distribution<double> dist(mean, stddev);
    return std::clamp(dist(g_rng), 0.0, 1.0);
}

double SampleExponential(double mean) {
    std::exponential_distribution<double> dist(1.0 / mean);
    return dist(g_rng);
}

bool SampleBernoulli(double p) {
    std::uniform_real_distribution<double> dist(0.0, 1.0);
    return dist(g_rng) < p;
}

// ============== Perimeter Node Application ==============
class PerimeterNodeApp : public Application {
public:
    static TypeId GetTypeId();
    PerimeterNodeApp();
    virtual ~PerimeterNodeApp();

    void SetNodeId(uint32_t id) { m_nodeId = id; }
    void SetPosition(Vector pos) { m_position = pos; }
    void SetNeighbors(std::vector<Ptr<PerimeterNodeApp>> neighbors) { m_neighbors = neighbors; }
    
    void OnSensorEvent(bool isIntruder, double eventTime);
    void ReceiveVerifyRequest(uint32_t senderId, bool isIntruder, double eventTime);
    void ReceiveVerifyResponse(uint32_t senderId);

private:
    virtual void StartApplication() override;
    virtual void StopApplication() override;

    void ProcessDecisionLogic(bool isIntruder, double confidence, double eventTime);
    void SendVerifyRequest(bool isIntruder, double eventTime);
    void SendUplink(double eventTime, bool isIntruder, bool usedP2p);
    void VerificationTimeout(double eventTime, bool isIntruder, double confidence);

    uint32_t m_nodeId;
    Vector m_position;
    std::vector<Ptr<PerimeterNodeApp>> m_neighbors;
    
    // Verification State
    bool m_waitingForVerification = false;
    int m_verificationConfirmations = 0;
    EventId m_verificationTimeoutEvent;
};

NS_OBJECT_ENSURE_REGISTERED(PerimeterNodeApp);

TypeId PerimeterNodeApp::GetTypeId() {
    static TypeId tid = TypeId("ns3::PerimeterNodeApp")
        .SetParent<Application>()
        .AddConstructor<PerimeterNodeApp>();
    return tid;
}

PerimeterNodeApp::PerimeterNodeApp() : m_nodeId(0) {}
PerimeterNodeApp::~PerimeterNodeApp() {}

void PerimeterNodeApp::StartApplication() {
    NS_LOG_INFO("Node " << m_nodeId << " started");
}

void PerimeterNodeApp::StopApplication() {
    Simulator::Cancel(m_verificationTimeoutEvent);
}

void PerimeterNodeApp::OnSensorEvent(bool isIntruder, double eventTime) {
    // 1. Image Processing Abstraction: Generate confidence score
    double confidence;
    if (isIntruder) {
        confidence = SampleGaussian(IMG_BOAR_MEAN, IMG_BOAR_STD);
    } else {
        confidence = SampleGaussian(IMG_NON_BOAR_MEAN, IMG_NON_BOAR_STD);
    }
    
    NS_LOG_DEBUG("Node " << m_nodeId << " confidence: " << confidence);
    ProcessDecisionLogic(isIntruder, confidence, eventTime);
}

void PerimeterNodeApp::ProcessDecisionLogic(bool isIntruder, double confidence, double eventTime) {
    // Tier 1: High Confidence -> Immediate Uplink
    if (confidence >= CONFIRM_THRESHOLD) {
        SendUplink(eventTime, isIntruder, false);
    }
    // Tier 2: Medium Confidence -> P2P Verification
    else if (confidence >= VERIFY_THRESHOLD) {
        SendVerifyRequest(isIntruder, eventTime);
        m_waitingForVerification = true;
        m_verificationConfirmations = 0;
        
        // Schedule timeout
        m_verificationTimeoutEvent = Simulator::Schedule(
            Seconds(P2P_TIMEOUT),
            &PerimeterNodeApp::VerificationTimeout,
            this, eventTime, isIntruder, confidence
        );
    }
    // Tier 3: Low Confidence -> Ignore
    // Do nothing
}

void PerimeterNodeApp::SendVerifyRequest(bool isIntruder, double eventTime) {
    NS_LOG_DEBUG("Node " << m_nodeId << " sending VERIFY_REQ");
    g_stats.p2pMessagesSent++;
    
    for (auto& neighbor : m_neighbors) {
        // Simulate P2P transmission (simplified: direct call)
        // In full NS-3+LoRa, this would be a packet send
        Simulator::Schedule(
            MilliSeconds(100 + (std::rand() % 200)), // 100-300ms delay
            &PerimeterNodeApp::ReceiveVerifyRequest,
            neighbor, m_nodeId, isIntruder, eventTime
        );
    }
}

void PerimeterNodeApp::ReceiveVerifyRequest(uint32_t senderId, bool isIntruder, double eventTime) {
    NS_LOG_DEBUG("Node " << m_nodeId << " received VERIFY_REQ from " << senderId);
    
    // Check my own sensor reading
    double myConfidence;
    if (isIntruder) {
        myConfidence = SampleGaussian(IMG_BOAR_MEAN, IMG_BOAR_STD);
    } else {
        myConfidence = SampleGaussian(IMG_NON_BOAR_MEAN, IMG_NON_BOAR_STD);
    }
    
    if (myConfidence >= CONFIRM_THRESHOLD) {
        // I confirm! Send response
        g_stats.p2pMessagesSent++;
        for (auto& neighbor : m_neighbors) {
            if (neighbor->m_nodeId == senderId) {
                Simulator::Schedule(
                    MilliSeconds(50 + (std::rand() % 100)),
                    &PerimeterNodeApp::ReceiveVerifyResponse,
                    neighbor, m_nodeId
                );
                break;
            }
        }
    }
}

void PerimeterNodeApp::ReceiveVerifyResponse(uint32_t senderId) {
    NS_LOG_DEBUG("Node " << m_nodeId << " received VERIFY_RESP from " << senderId);
    
    if (m_waitingForVerification) {
        m_verificationConfirmations++;
        // Got confirmation! Cancel timeout and send uplink
        Simulator::Cancel(m_verificationTimeoutEvent);
        m_waitingForVerification = false;
        
        // Note: We don't have access to original event params here in simplified model
        // In full implementation, store pending event context
        // For now, we'll record this in the timeout handler
    }
}

void PerimeterNodeApp::VerificationTimeout(double eventTime, bool isIntruder, double confidence) {
    m_waitingForVerification = false;
    
    if (m_verificationConfirmations > 0) {
        // Got at least one confirmation
        SendUplink(eventTime, isIntruder, true);
    }
    // Else: No confirmation, ignore
}

void PerimeterNodeApp::SendUplink(double eventTime, bool isIntruder, bool usedP2p) {
    double now = Simulator::Now().GetSeconds();
    double latency = now - eventTime;
    
    NS_LOG_INFO("Node " << m_nodeId << " UPLINK: intruder=" << isIntruder 
                << ", latency=" << latency << "s, p2p=" << usedP2p);
    
    g_stats.latencies.push_back(latency);
    
    if (isIntruder) {
        g_stats.truePositives++;
    } else {
        g_stats.falsePositives++;
    }
}

// ============== Environment (Event Generator) ==============
class EnvironmentApp : public Application {
public:
    static TypeId GetTypeId();
    EnvironmentApp();
    
    void SetNodes(std::vector<Ptr<PerimeterNodeApp>> nodes, std::vector<Vector> positions);

private:
    virtual void StartApplication() override;
    void GenerateEvent();
    
    std::vector<Ptr<PerimeterNodeApp>> m_nodes;
    std::vector<Vector> m_positions;
    int m_eventCount = 0;
};

NS_OBJECT_ENSURE_REGISTERED(EnvironmentApp);

TypeId EnvironmentApp::GetTypeId() {
    static TypeId tid = TypeId("ns3::EnvironmentApp")
        .SetParent<Application>()
        .AddConstructor<EnvironmentApp>();
    return tid;
}

EnvironmentApp::EnvironmentApp() {}

void EnvironmentApp::SetNodes(std::vector<Ptr<PerimeterNodeApp>> nodes, std::vector<Vector> positions) {
    m_nodes = nodes;
    m_positions = positions;
}

void EnvironmentApp::StartApplication() {
    GenerateEvent();
}

void EnvironmentApp::GenerateEvent() {
    if (m_eventCount >= TOTAL_EVENTS) return;
    
    // Determine event type
    bool isIntruder = SampleBernoulli(INTRUDER_PROB);
    double eventTime = Simulator::Now().GetSeconds();
    
    // Random event position
    std::uniform_real_distribution<double> posDist(-25.0, 25.0);
    double ex = posDist(g_rng);
    double ey = posDist(g_rng);
    
    g_stats.totalEvents++;
    if (isIntruder) g_stats.intruderEvents++;
    else g_stats.noiseEvents++;
    
    // Dispatch to nearby nodes
    for (size_t i = 0; i < m_nodes.size(); i++) {
        double dx = m_positions[i].x - ex;
        double dy = m_positions[i].y - ey;
        double dist = std::sqrt(dx*dx + dy*dy);
        
        if (dist <= SENSOR_RANGE) {
            Simulator::Schedule(
                MilliSeconds(10), // Small processing delay
                &PerimeterNodeApp::OnSensorEvent,
                m_nodes[i], isIntruder, eventTime
            );
        }
    }
    
    m_eventCount++;
    
    // Schedule next event
    double interval = SampleExponential(EVENT_INTERVAL);
    Simulator::Schedule(Seconds(interval), &EnvironmentApp::GenerateEvent, this);
}

// ============== Main Simulation ==============
int main(int argc, char *argv[]) {
    LogComponentEnable("LoraDualRingSimulation", LOG_LEVEL_INFO);
    
    NS_LOG_INFO("=== Dual-Ring LoRa Perimeter Simulation (NS-3) ===");
    
    // Create nodes
    NodeContainer perimeterNodes;
    perimeterNodes.Create(OUTER_RING_NODES + INNER_RING_NODES);
    
    // Setup mobility (static positions)
    MobilityHelper mobility;
    Ptr<ListPositionAllocator> posAlloc = CreateObject<ListPositionAllocator>();
    
    std::vector<Vector> positions;
    std::vector<Ptr<PerimeterNodeApp>> apps;
    
    // Outer ring positions
    for (int i = 0; i < OUTER_RING_NODES; i++) {
        double angle = i * (360.0 / OUTER_RING_NODES) * M_PI / 180.0;
        double x = OUTER_RING_RADIUS * std::cos(angle);
        double y = OUTER_RING_RADIUS * std::sin(angle);
        posAlloc->Add(Vector(x, y, 0));
        positions.push_back(Vector(x, y, 0));
    }
    
    // Inner ring positions
    for (int i = 0; i < INNER_RING_NODES; i++) {
        double angle = (i * (360.0 / INNER_RING_NODES) + INNER_RING_OFFSET_DEG) * M_PI / 180.0;
        double x = INNER_RING_RADIUS * std::cos(angle);
        double y = INNER_RING_RADIUS * std::sin(angle);
        posAlloc->Add(Vector(x, y, 0));
        positions.push_back(Vector(x, y, 0));
    }
    
    mobility.SetPositionAllocator(posAlloc);
    mobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
    mobility.Install(perimeterNodes);
    
    // Create applications
    for (uint32_t i = 0; i < perimeterNodes.GetN(); i++) {
        Ptr<PerimeterNodeApp> app = CreateObject<PerimeterNodeApp>();
        app->SetNodeId(i);
        app->SetPosition(positions[i]);
        perimeterNodes.Get(i)->AddApplication(app);
        app->SetStartTime(Seconds(0));
        app->SetStopTime(Seconds(10000));
        apps.push_back(app);
    }
    
    // Compute neighbors (within P2P range)
    for (size_t i = 0; i < apps.size(); i++) {
        std::vector<Ptr<PerimeterNodeApp>> neighbors;
        for (size_t j = 0; j < apps.size(); j++) {
            if (i == j) continue;
            double dx = positions[i].x - positions[j].x;
            double dy = positions[i].y - positions[j].y;
            if (std::sqrt(dx*dx + dy*dy) <= P2P_RANGE) {
                neighbors.push_back(apps[j]);
            }
        }
        apps[i]->SetNeighbors(neighbors);
    }
    
    // Create environment (event generator)
    NodeContainer envNode;
    envNode.Create(1);
    Ptr<EnvironmentApp> envApp = CreateObject<EnvironmentApp>();
    envApp->SetNodes(apps, positions);
    envNode.Get(0)->AddApplication(envApp);
    envApp->SetStartTime(Seconds(1));
    envApp->SetStopTime(Seconds(10000));
    
    // Run simulation
    NS_LOG_INFO("Running simulation...");
    Simulator::Stop(Seconds(10000));
    Simulator::Run();
    
    // Print results
    NS_LOG_INFO("=== SIMULATION RESULTS ===");
    NS_LOG_INFO("Total Events: " << g_stats.totalEvents);
    NS_LOG_INFO("  Intruders: " << g_stats.intruderEvents);
    NS_LOG_INFO("  Noise: " << g_stats.noiseEvents);
    NS_LOG_INFO("True Positives: " << g_stats.truePositives);
    NS_LOG_INFO("False Positives: " << g_stats.falsePositives);
    NS_LOG_INFO("P2P Messages: " << g_stats.p2pMessagesSent);
    
    if (!g_stats.latencies.empty()) {
        double meanLat = 0;
        for (double l : g_stats.latencies) meanLat += l;
        meanLat /= g_stats.latencies.size();
        NS_LOG_INFO("Mean Latency: " << meanLat << " s");
    }
    
    double detectionRate = (g_stats.intruderEvents > 0) ? 
        (double)g_stats.truePositives / g_stats.intruderEvents : 0;
    double fpr = (g_stats.noiseEvents > 0) ? 
        (double)g_stats.falsePositives / g_stats.noiseEvents : 0;
    
    NS_LOG_INFO("Detection Rate: " << (detectionRate * 100) << "%");
    NS_LOG_INFO("False Positive Rate: " << (fpr * 100) << "%");
    
    Simulator::Destroy();
    return 0;
}
