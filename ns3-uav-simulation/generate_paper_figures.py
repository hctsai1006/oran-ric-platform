#!/usr/bin/env python3
"""
Generate Paper-Quality Figures for ns-3 + xApp Integration Results
"""

import json
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from pathlib import Path
from datetime import datetime

# Set publication quality settings
plt.rcParams.update({
    'font.size': 12,
    'font.family': 'serif',
    'axes.labelsize': 14,
    'axes.titlesize': 14,
    'xtick.labelsize': 12,
    'ytick.labelsize': 12,
    'legend.fontsize': 11,
    'figure.figsize': (10, 6),
    'figure.dpi': 150,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight'
})

def load_results(json_path):
    with open(json_path, 'r') as f:
        return json.load(f)

def generate_rsrp_timeline(results, output_dir):
    """Generate RSRP timeline with cell handover annotations"""
    fig, ax = plt.subplots(figsize=(12, 6))

    decisions = results['xapp_decisions']
    times = [d['time'] for d in decisions]
    rsrps = [d['rsrp'] for d in decisions]
    cells = [d['cell_id'] for d in decisions]

    # Color by cell
    colors = {1: '#2196F3', 2: '#4CAF50', 3: '#FF9800'}
    cell_names = {1: 'eNB 1', 2: 'eNB 2', 3: 'eNB 3'}

    # Plot RSRP with color segments by cell
    prev_cell = cells[0]
    segment_start = 0

    for i in range(1, len(cells)):
        if cells[i] != prev_cell or i == len(cells) - 1:
            end_idx = i if cells[i] != prev_cell else i + 1
            ax.plot(times[segment_start:end_idx], rsrps[segment_start:end_idx],
                   color=colors[prev_cell], linewidth=2.5, label=cell_names[prev_cell] if segment_start == 0 or prev_cell not in [cells[j] for j in range(segment_start)] else '')

            # Mark handover point
            if cells[i] != prev_cell:
                ax.axvline(x=times[i], color='red', linestyle='--', alpha=0.7, linewidth=1.5)
                ax.annotate(f'HO\n{cell_names[prev_cell]}→{cell_names[cells[i]]}',
                           xy=(times[i], rsrps[i]), xytext=(times[i]+2, rsrps[i]+3),
                           fontsize=9, ha='left',
                           arrowprops=dict(arrowstyle='->', color='red', alpha=0.7))

            segment_start = i
            prev_cell = cells[i]

    # Threshold lines
    ax.axhline(y=-110, color='orange', linestyle=':', alpha=0.8, linewidth=1.5, label='RSRP Threshold (-110 dBm)')
    ax.axhline(y=-120, color='red', linestyle=':', alpha=0.8, linewidth=1.5, label='Critical Threshold (-120 dBm)')

    ax.set_xlabel('Simulation Time (s)')
    ax.set_ylabel('RSRP (dBm)')
    ax.set_title('UAV RSRP Timeline with Cell Handovers (ns-3 LTE Simulation)')
    ax.grid(True, alpha=0.3)
    ax.set_xlim(0, max(times))
    ax.set_ylim(-125, -100)

    # Custom legend
    handles = [mpatches.Patch(color=colors[i], label=cell_names[i]) for i in [1, 2, 3]]
    handles.append(plt.Line2D([0], [0], color='red', linestyle='--', label='Handover Event'))
    ax.legend(handles=handles, loc='upper right')

    plt.tight_layout()
    plt.savefig(output_dir / 'rsrp_timeline_handover.png')
    plt.savefig(output_dir / 'rsrp_timeline_handover.pdf')
    plt.close()
    print(f"Saved: rsrp_timeline_handover.png/pdf")

def generate_xapp_decisions_chart(results, output_dir):
    """Generate xApp decision statistics"""
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    decisions = results['xapp_decisions']

    # PRB allocation over time
    ax1 = axes[0]
    times = [d['time'] for d in decisions]
    prbs = [d['decision']['prb_quota'] for d in decisions]

    ax1.bar(times, prbs, width=0.8, color='#3F51B5', alpha=0.8)
    ax1.set_xlabel('Simulation Time (s)')
    ax1.set_ylabel('PRB Quota')
    ax1.set_title('xApp PRB Resource Allocation')
    ax1.grid(True, alpha=0.3, axis='y')

    # Decision type distribution
    ax2 = axes[1]
    maintain = results['maintain_decisions']
    handover = results['handover_recommendations']

    labels = ['Maintain\n(Stay on Cell)', 'Handover\n(Switch Cell)']
    values = [maintain, handover]
    colors = ['#4CAF50', '#FF5722']

    bars = ax2.bar(labels, values, color=colors, alpha=0.8, edgecolor='black')
    ax2.set_ylabel('Number of Decisions')
    ax2.set_title('xApp Decision Distribution')

    # Add value labels
    for bar, val in zip(bars, values):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                str(val), ha='center', va='bottom', fontsize=12, fontweight='bold')

    plt.tight_layout()
    plt.savefig(output_dir / 'xapp_decisions.png')
    plt.savefig(output_dir / 'xapp_decisions.pdf')
    plt.close()
    print(f"Saved: xapp_decisions.png/pdf")

def generate_uav_trajectory(results, output_dir):
    """Generate UAV trajectory with cell coverage"""
    fig, ax = plt.subplots(figsize=(10, 8))

    # eNB positions
    enbs = {
        1: (200, 200, 'eNB 1'),
        2: (500, 500, 'eNB 2'),
        3: (800, 200, 'eNB 3')
    }

    # UAV waypoints
    waypoints = [
        (0, 100, 100),
        (15, 250, 250),
        (30, 400, 400),
        (45, 550, 550),
        (60, 700, 350),
        (75, 850, 200)
    ]

    # Draw cell coverage circles
    colors = {1: '#2196F3', 2: '#4CAF50', 3: '#FF9800'}
    for cell_id, (x, y, name) in enbs.items():
        circle = plt.Circle((x, y), 300, color=colors[cell_id], alpha=0.15)
        ax.add_patch(circle)
        ax.plot(x, y, '^', markersize=20, color=colors[cell_id], markeredgecolor='black')
        ax.annotate(name, (x, y+40), ha='center', fontsize=11, fontweight='bold')

    # Draw UAV trajectory
    uav_x = [w[1] for w in waypoints]
    uav_y = [w[2] for w in waypoints]

    ax.plot(uav_x, uav_y, 'o-', color='#E91E63', linewidth=3, markersize=10,
           markeredgecolor='black', label='UAV Flight Path')

    # Annotate waypoints
    for t, x, y in waypoints:
        ax.annotate(f't={t}s', (x+15, y+15), fontsize=9)

    ax.set_xlabel('X Position (m)')
    ax.set_ylabel('Y Position (m)')
    ax.set_title('UAV Trajectory with LTE Cell Coverage (3GPP TR 36.777 Scenario)')
    ax.set_xlim(0, 1000)
    ax.set_ylim(0, 700)
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='lower right')

    plt.tight_layout()
    plt.savefig(output_dir / 'uav_trajectory.png')
    plt.savefig(output_dir / 'uav_trajectory.pdf')
    plt.close()
    print(f"Saved: uav_trajectory.png/pdf")

def generate_sinr_analysis(results, output_dir):
    """Generate SINR analysis chart"""
    fig, ax = plt.subplots(figsize=(12, 5))

    decisions = results['xapp_decisions']
    times = [d['time'] for d in decisions]
    sinrs = [d['sinr'] for d in decisions]
    cells = [d['cell_id'] for d in decisions]

    colors = {1: '#2196F3', 2: '#4CAF50', 3: '#FF9800'}

    for i in range(len(times)):
        ax.bar(times[i], sinrs[i], width=0.8, color=colors[cells[i]], alpha=0.8)

    ax.axhline(y=10, color='green', linestyle='--', alpha=0.7, label='Good SINR (>10 dB)')
    ax.axhline(y=0, color='red', linestyle='--', alpha=0.7, label='Poor SINR (<0 dB)')

    ax.set_xlabel('Simulation Time (s)')
    ax.set_ylabel('SINR (dB)')
    ax.set_title('UAV SINR over Time (ns-3 LTE Simulation)')
    ax.grid(True, alpha=0.3, axis='y')
    ax.legend(loc='upper right')

    plt.tight_layout()
    plt.savefig(output_dir / 'sinr_analysis.png')
    plt.savefig(output_dir / 'sinr_analysis.pdf')
    plt.close()
    print(f"Saved: sinr_analysis.png/pdf")

def generate_summary_table(results, output_dir):
    """Generate summary statistics"""
    decisions = results['xapp_decisions']

    rsrps = [d['rsrp'] for d in decisions]
    sinrs = [d['sinr'] for d in decisions]

    summary = {
        'Simulation Duration': '75 seconds',
        'Total Samples': results['total_samples'],
        'Average RSRP': f"{results['avg_rsrp']:.2f} dBm",
        'Min RSRP': f"{min(rsrps):.2f} dBm",
        'Max RSRP': f"{max(rsrps):.2f} dBm",
        'Average SINR': f"{np.mean(sinrs):.2f} dB",
        'Handover Events': 2,  # Cell 1→2, Cell 2→3
        'xApp Maintain Decisions': results['maintain_decisions'],
        'xApp Handover Recommendations': results['handover_recommendations'],
        'PRB Quota (constant)': decisions[0]['decision']['prb_quota'],
        'Slice Type': decisions[0]['decision']['slice_id'].upper()
    }

    # Save as text
    with open(output_dir / 'summary_statistics.txt', 'w') as f:
        f.write("=" * 60 + "\n")
        f.write("ns-3 UAV LTE + xApp Integration Test Summary\n")
        f.write("=" * 60 + "\n\n")
        for key, value in summary.items():
            f.write(f"{key:35s}: {value}\n")
        f.write("\n" + "=" * 60 + "\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")

    print(f"Saved: summary_statistics.txt")
    return summary

def main():
    # Paths
    results_path = Path('/home/thc1006/dev/oran-ric-platform/ns3-uav-simulation/results/ns3-lte/ns3_xapp_full_integration.json')
    output_dir = Path('/home/thc1006/dev/oran-ric-platform/ns3-uav-simulation/results/figures')
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Generating Paper-Quality Figures")
    print("=" * 60)

    results = load_results(results_path)

    generate_rsrp_timeline(results, output_dir)
    generate_xapp_decisions_chart(results, output_dir)
    generate_uav_trajectory(results, output_dir)
    generate_sinr_analysis(results, output_dir)
    summary = generate_summary_table(results, output_dir)

    print("\n" + "=" * 60)
    print("Summary Statistics:")
    print("=" * 60)
    for key, value in summary.items():
        print(f"  {key}: {value}")
    print("=" * 60)
    print(f"\nAll figures saved to: {output_dir}")

if __name__ == "__main__":
    main()
