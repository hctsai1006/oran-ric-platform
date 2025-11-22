#!/usr/bin/env python3
"""
Generate Publication-Quality O-RAN System Architecture Diagram
for UAV xApp Paper (IEEE/ACM Format)

This script creates a comprehensive system architecture diagram showing:
- O-RAN architecture layers (Non-RT RIC, Near-RT RIC, E2 Nodes)
- Key interfaces (A1, E2, O1)
- UAV Policy xApp components
- Data flow for measurements and control decisions
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle, Circle
from matplotlib.patches import ConnectionPatch
import matplotlib.lines as mlines
import numpy as np
from pathlib import Path

# Publication-quality settings for IEEE/ACM
plt.rcParams.update({
    'font.size': 10,
    'font.family': 'serif',
    'font.serif': ['Times New Roman', 'Times', 'DejaVu Serif'],
    'axes.labelsize': 11,
    'axes.titlesize': 12,
    'xtick.labelsize': 9,
    'ytick.labelsize': 9,
    'legend.fontsize': 9,
    'figure.figsize': (12, 10),
    'figure.dpi': 150,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'text.usetex': False,  # Set True if LaTeX is available
    'axes.linewidth': 0.8,
    'lines.linewidth': 1.5,
})


def create_rounded_box(ax, x, y, width, height, color, alpha=0.3,
                       linewidth=2, linestyle='-', edgecolor='black',
                       label=None, fontsize=10, fontweight='bold',
                       text_color='black', zorder=1):
    """Create a rounded rectangle box with optional label"""
    box = FancyBboxPatch(
        (x - width/2, y - height/2), width, height,
        boxstyle="round,pad=0.02,rounding_size=0.05",
        facecolor=color, alpha=alpha,
        edgecolor=edgecolor, linewidth=linewidth,
        linestyle=linestyle, zorder=zorder
    )
    ax.add_patch(box)

    if label:
        ax.text(x, y, label, ha='center', va='center',
                fontsize=fontsize, fontweight=fontweight,
                color=text_color, zorder=zorder+1)

    return box


def create_arrow(ax, start, end, color='black', style='->',
                 linewidth=1.5, connectionstyle='arc3,rad=0',
                 shrinkA=5, shrinkB=5, zorder=3):
    """Create an arrow between two points"""
    arrow = FancyArrowPatch(
        start, end,
        arrowstyle=style,
        color=color,
        linewidth=linewidth,
        connectionstyle=connectionstyle,
        shrinkA=shrinkA,
        shrinkB=shrinkB,
        zorder=zorder
    )
    ax.add_patch(arrow)
    return arrow


def create_dashed_arrow(ax, start, end, color='black', linewidth=1.5,
                        label=None, label_pos=0.5, label_offset=(0, 5)):
    """Create a dashed arrow with optional label"""
    arrow = FancyArrowPatch(
        start, end,
        arrowstyle='->',
        color=color,
        linewidth=linewidth,
        linestyle='--',
        shrinkA=5,
        shrinkB=5,
        zorder=3
    )
    ax.add_patch(arrow)

    if label:
        mid_x = start[0] + label_pos * (end[0] - start[0]) + label_offset[0]
        mid_y = start[1] + label_pos * (end[1] - start[1]) + label_offset[1]
        ax.text(mid_x, mid_y, label, fontsize=8, ha='center', va='bottom',
                style='italic', color=color)

    return arrow


def generate_oran_architecture_diagram():
    """Generate the complete O-RAN architecture diagram"""

    fig, ax = plt.subplots(figsize=(14, 11))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_aspect('equal')
    ax.axis('off')

    # Color scheme (professional, publication-ready)
    colors = {
        'smo': '#E3F2FD',           # Light blue for SMO/Non-RT RIC
        'near_rt': '#E8F5E9',       # Light green for Near-RT RIC
        'xapp_highlight': '#FFEB3B', # Yellow highlight for UAV Policy xApp
        'e2_node': '#FFF3E0',       # Light orange for E2 nodes
        'uav': '#FCE4EC',           # Light pink for UAV
        'interface': '#37474F',      # Dark gray for interfaces
        'dataflow_up': '#1565C0',    # Blue for upward data flow
        'dataflow_down': '#C62828',  # Red for downward control flow
        'component': '#ECEFF1',      # Light gray for internal components
        'metrics': '#7B1FA2',        # Purple for metrics
    }

    # ==========================================================================
    # Layer 1: SMO / Non-RT RIC (Top)
    # ==========================================================================

    # SMO outer boundary
    create_rounded_box(ax, 50, 88, 80, 16, colors['smo'], alpha=0.4,
                       linewidth=2.5, edgecolor='#1565C0')
    ax.text(50, 95, 'Service Management and Orchestration (SMO)',
            ha='center', va='center', fontsize=12, fontweight='bold',
            color='#0D47A1')

    # Non-RT RIC
    create_rounded_box(ax, 35, 85, 28, 8, colors['smo'], alpha=0.6,
                       linewidth=1.5, edgecolor='#1976D2',
                       label='Non-RT RIC', fontsize=10)

    # rApps container
    create_rounded_box(ax, 65, 85, 28, 8, colors['component'], alpha=0.5,
                       linewidth=1, edgecolor='#546E7A',
                       label='rApps / AI/ML', fontsize=9)

    # ==========================================================================
    # Layer 2: Near-RT RIC (Middle-Upper)
    # ==========================================================================

    # Near-RT RIC outer boundary
    create_rounded_box(ax, 50, 62, 80, 28, colors['near_rt'], alpha=0.4,
                       linewidth=2.5, edgecolor='#2E7D32')
    ax.text(50, 74.5, 'Near-RT RIC Platform', ha='center', va='center',
            fontsize=12, fontweight='bold', color='#1B5E20')

    # xApp Container area
    create_rounded_box(ax, 50, 67, 70, 10, '#C8E6C9', alpha=0.5,
                       linewidth=1.5, edgecolor='#388E3C', linestyle='--')
    ax.text(15, 67, 'xApps', ha='left', va='center', fontsize=9,
            fontweight='bold', color='#2E7D32', rotation=90)

    # UAV Policy xApp (HIGHLIGHTED)
    create_rounded_box(ax, 35, 67, 22, 8, colors['xapp_highlight'], alpha=0.9,
                       linewidth=3, edgecolor='#F57F17',
                       label='UAV Policy xApp', fontsize=10, fontweight='bold')
    # Star marker for emphasis
    ax.plot(24, 70, '*', markersize=12, color='#E65100', zorder=5)

    # Other xApps
    create_rounded_box(ax, 58, 67, 18, 8, colors['component'], alpha=0.5,
                       linewidth=1, edgecolor='#546E7A',
                       label='Traffic Steering\nxApp', fontsize=8)

    create_rounded_box(ax, 77, 67, 18, 8, colors['component'], alpha=0.5,
                       linewidth=1, edgecolor='#546E7A',
                       label='QoS/QoE\nxApp', fontsize=8)

    # Near-RT RIC internal components
    # SDL (Shared Data Layer)
    create_rounded_box(ax, 28, 55, 16, 6, '#B2DFDB', alpha=0.8,
                       linewidth=1.5, edgecolor='#00695C',
                       label='SDL', fontsize=9, fontweight='bold')
    ax.text(28, 51.5, '(Redis)', ha='center', va='center', fontsize=7,
            color='#004D40', style='italic')

    # RMR Messaging
    create_rounded_box(ax, 50, 55, 20, 6, '#BBDEFB', alpha=0.8,
                       linewidth=1.5, edgecolor='#1565C0',
                       label='RMR Messaging', fontsize=9, fontweight='bold')

    # E2 Termination
    create_rounded_box(ax, 72, 55, 16, 6, '#D1C4E9', alpha=0.8,
                       linewidth=1.5, edgecolor='#512DA8',
                       label='E2 Term', fontsize=9, fontweight='bold')

    # ==========================================================================
    # Layer 3: Prometheus/Grafana Monitoring (Side)
    # ==========================================================================

    # Monitoring stack
    create_rounded_box(ax, 95, 62, 8, 20, '#F3E5F5', alpha=0.6,
                       linewidth=1.5, edgecolor='#7B1FA2')
    ax.text(95, 70, 'Prometheus', ha='center', va='center', fontsize=7,
            fontweight='bold', color='#4A148C', rotation=90)
    ax.text(95, 57, 'Grafana', ha='center', va='center', fontsize=7,
            fontweight='bold', color='#4A148C', rotation=90)

    # ==========================================================================
    # Layer 4: E2 Nodes (CU/DU/RU)
    # ==========================================================================

    # E2 Nodes container
    create_rounded_box(ax, 50, 32, 80, 18, colors['e2_node'], alpha=0.4,
                       linewidth=2.5, edgecolor='#E65100')
    ax.text(50, 40, 'E2 Nodes (O-RAN Compliant)', ha='center', va='center',
            fontsize=11, fontweight='bold', color='#BF360C')

    # gNB/eNB components
    # gNB-CU
    create_rounded_box(ax, 25, 30, 18, 10, '#FFE0B2', alpha=0.7,
                       linewidth=1.5, edgecolor='#E65100')
    ax.text(25, 32, 'gNB-CU', ha='center', va='center', fontsize=9, fontweight='bold')
    ax.text(25, 28, '(Central Unit)', ha='center', va='center', fontsize=7,
            color='#BF360C', style='italic')

    # gNB-DU
    create_rounded_box(ax, 50, 30, 18, 10, '#FFE0B2', alpha=0.7,
                       linewidth=1.5, edgecolor='#E65100')
    ax.text(50, 32, 'gNB-DU', ha='center', va='center', fontsize=9, fontweight='bold')
    ax.text(50, 28, '(Distributed Unit)', ha='center', va='center', fontsize=7,
            color='#BF360C', style='italic')

    # O-RU
    create_rounded_box(ax, 75, 30, 18, 10, '#FFE0B2', alpha=0.7,
                       linewidth=1.5, edgecolor='#E65100')
    ax.text(75, 32, 'O-RU', ha='center', va='center', fontsize=9, fontweight='bold')
    ax.text(75, 28, '(Radio Unit)', ha='center', va='center', fontsize=7,
            color='#BF360C', style='italic')

    # ns-3 Simulator indicator
    create_rounded_box(ax, 50, 23.5, 35, 4, '#E0E0E0', alpha=0.8,
                       linewidth=1, edgecolor='#757575', linestyle=':',
                       label='ns-3 LTE Simulation (E2SM-KPM)', fontsize=8)

    # ==========================================================================
    # Layer 5: UAV UE (Bottom)
    # ==========================================================================

    # UAV representation
    create_rounded_box(ax, 50, 10, 25, 10, colors['uav'], alpha=0.6,
                       linewidth=2, edgecolor='#AD1457')
    ax.text(50, 12, 'UAV UE', ha='center', va='center', fontsize=10, fontweight='bold')
    ax.text(50, 8, '(User Equipment)', ha='center', va='center', fontsize=8,
            color='#880E4F', style='italic')

    # UAV icon (simple drone shape)
    ax.plot([42, 44, 46], [10, 12, 10], 'k-', linewidth=1.5)
    ax.plot([54, 56, 58], [10, 12, 10], 'k-', linewidth=1.5)
    ax.plot(44, 12, 'o', markersize=4, color='#AD1457')
    ax.plot(56, 12, 'o', markersize=4, color='#AD1457')

    # ==========================================================================
    # Interfaces (A1, E2, O1)
    # ==========================================================================

    # A1 Interface (Non-RT RIC to Near-RT RIC)
    create_arrow(ax, (35, 81), (35, 75), color=colors['interface'],
                 linewidth=2.5, style='->')
    create_arrow(ax, (38, 75), (38, 81), color=colors['interface'],
                 linewidth=2.5, style='->')
    ax.text(29, 78, 'A1', ha='center', va='center', fontsize=10,
            fontweight='bold', color='#37474F',
            bbox=dict(boxstyle='round', facecolor='white', edgecolor='#37474F'))
    ax.text(29, 76, '(Policy)', ha='center', va='center', fontsize=7,
            color='#546E7A', style='italic')

    # O1 Interface (SMO to E2 Nodes - side)
    create_arrow(ax, (12, 88), (12, 32), color=colors['interface'],
                 linewidth=2, style='<->', connectionstyle='arc3,rad=0')
    ax.text(7, 60, 'O1', ha='center', va='center', fontsize=10,
            fontweight='bold', color='#37474F',
            bbox=dict(boxstyle='round', facecolor='white', edgecolor='#37474F'))
    ax.text(7, 56, '(Mgmt)', ha='center', va='center', fontsize=7,
            color='#546E7A', style='italic')

    # E2 Interface (Near-RT RIC to E2 Nodes)
    create_arrow(ax, (50, 49), (50, 41), color=colors['interface'],
                 linewidth=2.5, style='->')
    create_arrow(ax, (55, 41), (55, 49), color=colors['interface'],
                 linewidth=2.5, style='->')
    ax.text(60, 45, 'E2', ha='center', va='center', fontsize=10,
            fontweight='bold', color='#37474F',
            bbox=dict(boxstyle='round', facecolor='white', edgecolor='#37474F'))
    ax.text(60, 42, '(Control)', ha='center', va='center', fontsize=7,
            color='#546E7A', style='italic')

    # ==========================================================================
    # Data Flow Arrows
    # ==========================================================================

    # RSRP/SINR measurements (UAV -> E2 Nodes -> Near-RT RIC -> xApp)
    # UAV to E2 (radio measurement)
    create_dashed_arrow(ax, (50, 15), (50, 24), color=colors['dataflow_up'],
                        linewidth=1.5, label='UE Measurements', label_offset=(-15, 2))

    # E2 to xApp (via E2 Term and RMR)
    create_dashed_arrow(ax, (72, 58), (72, 63), color=colors['dataflow_up'],
                        linewidth=1.5)
    create_dashed_arrow(ax, (58, 61), (45, 63), color=colors['dataflow_up'],
                        linewidth=1.5, label='RSRP/SINR', label_offset=(0, 3))

    # PRB Allocation (xApp -> E2 Nodes)
    create_dashed_arrow(ax, (30, 63), (30, 55), color=colors['dataflow_down'],
                        linewidth=1.5)
    create_dashed_arrow(ax, (25, 52), (25, 35), color=colors['dataflow_down'],
                        linewidth=1.5, label='PRB Allocation', label_offset=(-12, 10))

    # Handover commands
    create_dashed_arrow(ax, (40, 63), (50, 35), color=colors['dataflow_down'],
                        linewidth=1.5, label='Handover Cmd', label_offset=(8, 12))

    # Metrics to Prometheus
    create_dashed_arrow(ax, (86, 67), (91, 67), color=colors['metrics'],
                        linewidth=1.2, label='Metrics', label_offset=(0, 3))

    # ==========================================================================
    # Legend
    # ==========================================================================

    legend_y = 2
    legend_x = 5

    # Legend box
    legend_box = FancyBboxPatch(
        (legend_x - 2, legend_y - 2), 90, 6,
        boxstyle="round,pad=0.02",
        facecolor='white', alpha=0.9,
        edgecolor='#BDBDBD', linewidth=1
    )
    ax.add_patch(legend_box)

    # Legend items
    ax.text(legend_x, legend_y + 2, 'Legend:', fontsize=9, fontweight='bold')

    # Interface arrows
    ax.annotate('', xy=(legend_x + 12, legend_y + 1), xytext=(legend_x + 8, legend_y + 1),
                arrowprops=dict(arrowstyle='->', color=colors['interface'], lw=2))
    ax.text(legend_x + 14, legend_y + 1, 'Interface', fontsize=8, va='center')

    # Data flow up
    ax.annotate('', xy=(legend_x + 30, legend_y + 1), xytext=(legend_x + 26, legend_y + 1),
                arrowprops=dict(arrowstyle='->', color=colors['dataflow_up'], lw=1.5, ls='--'))
    ax.text(legend_x + 32, legend_y + 1, 'Measurement Flow', fontsize=8, va='center')

    # Data flow down
    ax.annotate('', xy=(legend_x + 56, legend_y + 1), xytext=(legend_x + 52, legend_y + 1),
                arrowprops=dict(arrowstyle='->', color=colors['dataflow_down'], lw=1.5, ls='--'))
    ax.text(legend_x + 58, legend_y + 1, 'Control Flow', fontsize=8, va='center')

    # Highlighted component
    highlight_patch = mpatches.Patch(facecolor=colors['xapp_highlight'],
                                     edgecolor='#F57F17', linewidth=2,
                                     label='Key Component')
    ax.add_patch(FancyBboxPatch((legend_x + 75, legend_y), 3, 2,
                                boxstyle="round", facecolor=colors['xapp_highlight'],
                                edgecolor='#F57F17', linewidth=2))
    ax.text(legend_x + 80, legend_y + 1, 'Highlighted', fontsize=8, va='center')

    # ==========================================================================
    # Title and Labels
    # ==========================================================================

    ax.text(50, 99, 'O-RAN Architecture for UAV Communication Management',
            ha='center', va='center', fontsize=14, fontweight='bold')
    ax.text(50, 97, '(UAV Policy xApp Integration with Near-RT RIC)',
            ha='center', va='center', fontsize=10, style='italic', color='#424242')

    return fig


def generate_detailed_xapp_diagram():
    """Generate detailed UAV Policy xApp internal architecture"""

    fig, ax = plt.subplots(figsize=(12, 8))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_aspect('equal')
    ax.axis('off')

    colors = {
        'main': '#FFEB3B',
        'component': '#E3F2FD',
        'data': '#E8F5E9',
        'policy': '#FFF3E0',
        'external': '#ECEFF1',
    }

    # Main xApp boundary
    create_rounded_box(ax, 50, 55, 85, 70, colors['main'], alpha=0.3,
                       linewidth=3, edgecolor='#F57F17')
    ax.text(50, 88, 'UAV Policy xApp', ha='center', va='center',
            fontsize=14, fontweight='bold', color='#E65100')

    # Policy Engine
    create_rounded_box(ax, 30, 70, 25, 12, colors['policy'], alpha=0.7,
                       linewidth=2, edgecolor='#E65100',
                       label='Policy Engine', fontsize=11, fontweight='bold')
    ax.text(30, 66, 'RSRP Threshold: -110 dBm\nSINR Threshold: 5 dB',
            ha='center', va='center', fontsize=8, color='#BF360C')

    # PRB Allocator
    create_rounded_box(ax, 70, 70, 25, 12, colors['policy'], alpha=0.7,
                       linewidth=2, edgecolor='#E65100',
                       label='PRB Allocator', fontsize=11, fontweight='bold')
    ax.text(70, 66, 'Quota: 50 PRBs\nSlice: URLLC',
            ha='center', va='center', fontsize=8, color='#BF360C')

    # Handover Controller
    create_rounded_box(ax, 50, 50, 30, 12, colors['component'], alpha=0.7,
                       linewidth=2, edgecolor='#1565C0',
                       label='Handover Controller', fontsize=11, fontweight='bold')
    ax.text(50, 46, 'A3 Event Handler\nHysteresis: 3 dB',
            ha='center', va='center', fontsize=8, color='#0D47A1')

    # HTTP REST API Server
    create_rounded_box(ax, 25, 32, 22, 10, colors['data'], alpha=0.7,
                       linewidth=1.5, edgecolor='#2E7D32',
                       label='REST API Server', fontsize=10, fontweight='bold')
    ax.text(25, 28.5, 'Port: 8080', ha='center', va='center', fontsize=8,
            color='#1B5E20', style='italic')

    # RMR Message Handler
    create_rounded_box(ax, 50, 32, 22, 10, colors['data'], alpha=0.7,
                       linewidth=1.5, edgecolor='#2E7D32',
                       label='RMR Handler', fontsize=10, fontweight='bold')
    ax.text(50, 28.5, 'Port: 4560', ha='center', va='center', fontsize=8,
            color='#1B5E20', style='italic')

    # Metrics Exporter
    create_rounded_box(ax, 75, 32, 22, 10, colors['data'], alpha=0.7,
                       linewidth=1.5, edgecolor='#2E7D32',
                       label='Metrics Exporter', fontsize=10, fontweight='bold')
    ax.text(75, 28.5, 'Prometheus Format', ha='center', va='center', fontsize=8,
            color='#1B5E20', style='italic')

    # External components
    # SDL
    create_rounded_box(ax, 12, 55, 12, 8, colors['external'], alpha=0.8,
                       linewidth=1.5, edgecolor='#546E7A',
                       label='SDL\n(Redis)', fontsize=9)

    # RMR
    create_rounded_box(ax, 88, 55, 12, 8, colors['external'], alpha=0.8,
                       linewidth=1.5, edgecolor='#546E7A',
                       label='RMR\nBus', fontsize=9)

    # Prometheus
    create_rounded_box(ax, 88, 32, 12, 8, colors['external'], alpha=0.8,
                       linewidth=1.5, edgecolor='#7B1FA2',
                       label='Prometheus', fontsize=8)

    # Arrows showing data flow
    # SDL connections
    create_arrow(ax, (18, 55), (25, 60), color='#00695C', linewidth=1.5)
    create_arrow(ax, (25, 50), (18, 55), color='#00695C', linewidth=1.5)

    # RMR connections
    create_arrow(ax, (82, 55), (75, 60), color='#1565C0', linewidth=1.5)
    create_arrow(ax, (75, 50), (82, 55), color='#1565C0', linewidth=1.5)

    # Internal flow
    create_arrow(ax, (30, 64), (35, 56), color='#424242', linewidth=1.2)
    create_arrow(ax, (70, 64), (65, 56), color='#424242', linewidth=1.2)
    create_arrow(ax, (50, 44), (50, 37), color='#424242', linewidth=1.2)

    # Metrics to Prometheus
    create_arrow(ax, (86, 32), (82, 32), color='#7B1FA2', linewidth=1.5)

    # Title
    ax.text(50, 96, 'UAV Policy xApp Internal Architecture',
            ha='center', va='center', fontsize=14, fontweight='bold')

    return fig


def generate_data_flow_diagram():
    """Generate data flow sequence diagram"""

    fig, ax = plt.subplots(figsize=(14, 10))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_aspect('equal')
    ax.axis('off')

    # Column positions for entities
    cols = {'uav': 15, 'e2': 35, 'ric': 55, 'xapp': 75, 'smo': 95}

    # Entity boxes at top
    entities = [
        ('UAV UE', cols['uav'], '#FCE4EC'),
        ('E2 Node\n(gNB)', cols['e2'], '#FFF3E0'),
        ('Near-RT RIC\n(E2 Term)', cols['ric'], '#E8F5E9'),
        ('UAV Policy\nxApp', cols['xapp'], '#FFEB3B'),
        ('Non-RT RIC\n(SMO)', cols['smo'], '#E3F2FD'),
    ]

    for name, x, color in entities:
        create_rounded_box(ax, x, 92, 14, 8, color, alpha=0.7,
                           linewidth=2, edgecolor='#424242',
                           label=name, fontsize=9, fontweight='bold')
        # Lifeline
        ax.plot([x, x], [88, 10], 'k--', linewidth=1, alpha=0.5)

    # Message sequence (top to bottom)
    y_pos = 82
    step = 8

    messages = [
        (cols['smo'], cols['xapp'], 'A1: ML Policy Update', '#1565C0', y_pos),
        (cols['uav'], cols['e2'], 'Radio: RSRP/SINR Report', '#AD1457', y_pos - step),
        (cols['e2'], cols['ric'], 'E2: RIC Indication', '#E65100', y_pos - 2*step),
        (cols['ric'], cols['xapp'], 'RMR: KPM Indication', '#2E7D32', y_pos - 3*step),
        (cols['xapp'], cols['xapp'], 'Process: Evaluate Policy', '#F57F17', y_pos - 4*step),
        (cols['xapp'], cols['ric'], 'RMR: Control Request', '#C62828', y_pos - 5*step),
        (cols['ric'], cols['e2'], 'E2: RIC Control', '#C62828', y_pos - 6*step),
        (cols['e2'], cols['uav'], 'Radio: PRB/Handover', '#C62828', y_pos - 7*step),
    ]

    for start_x, end_x, label, color, y in messages:
        if start_x == end_x:
            # Self message (loop back)
            ax.annotate('', xy=(start_x + 5, y - 2), xytext=(start_x, y),
                        arrowprops=dict(arrowstyle='->', color=color, lw=1.5))
            ax.plot([start_x, start_x + 5, start_x + 5, start_x],
                    [y, y, y - 2, y - 2], color=color, linewidth=1.5)
            ax.text(start_x + 7, y - 1, label, fontsize=8, va='center', color=color)
        else:
            ax.annotate('', xy=(end_x, y), xytext=(start_x, y),
                        arrowprops=dict(arrowstyle='->', color=color, lw=2))
            mid_x = (start_x + end_x) / 2
            ax.text(mid_x, y + 2, label, fontsize=8, ha='center', va='bottom',
                    color=color, fontweight='bold')

    # Title
    ax.text(50, 98, 'O-RAN Data Flow: UAV Measurement and Control Sequence',
            ha='center', va='center', fontsize=14, fontweight='bold')

    # Time arrow
    ax.annotate('', xy=(5, 10), xytext=(5, 85),
                arrowprops=dict(arrowstyle='->', color='black', lw=2))
    ax.text(3, 50, 'Time', fontsize=10, ha='center', va='center', rotation=90)

    return fig


def main():
    """Main function to generate all diagrams"""

    output_dir = Path('/home/thc1006/dev/oran-ric-platform/ns3-uav-simulation/results/figures')
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("Generating O-RAN System Architecture Diagrams")
    print("=" * 70)

    # Generate main architecture diagram
    print("\n[1/3] Generating main O-RAN architecture diagram...")
    fig1 = generate_oran_architecture_diagram()
    fig1.savefig(output_dir / 'oran_architecture.png', dpi=300,
                 bbox_inches='tight', facecolor='white', edgecolor='none')
    fig1.savefig(output_dir / 'oran_architecture.pdf', dpi=300,
                 bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.close(fig1)
    print("    Saved: oran_architecture.png, oran_architecture.pdf")

    # Generate detailed xApp diagram
    print("\n[2/3] Generating UAV Policy xApp internal architecture...")
    fig2 = generate_detailed_xapp_diagram()
    fig2.savefig(output_dir / 'xapp_internal_architecture.png', dpi=300,
                 bbox_inches='tight', facecolor='white', edgecolor='none')
    fig2.savefig(output_dir / 'xapp_internal_architecture.pdf', dpi=300,
                 bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.close(fig2)
    print("    Saved: xapp_internal_architecture.png, xapp_internal_architecture.pdf")

    # Generate data flow diagram
    print("\n[3/3] Generating data flow sequence diagram...")
    fig3 = generate_data_flow_diagram()
    fig3.savefig(output_dir / 'data_flow_sequence.png', dpi=300,
                 bbox_inches='tight', facecolor='white', edgecolor='none')
    fig3.savefig(output_dir / 'data_flow_sequence.pdf', dpi=300,
                 bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.close(fig3)
    print("    Saved: data_flow_sequence.png, data_flow_sequence.pdf")

    print("\n" + "=" * 70)
    print("All diagrams generated successfully!")
    print("=" * 70)
    print(f"\nOutput directory: {output_dir}")
    print("\nGenerated files:")
    print("  - oran_architecture.png/pdf       : Main O-RAN system architecture")
    print("  - xapp_internal_architecture.png/pdf : UAV Policy xApp internals")
    print("  - data_flow_sequence.png/pdf      : Data flow sequence diagram")
    print("\nAll figures are publication-ready at 300 DPI.")
    print("=" * 70)


if __name__ == "__main__":
    main()
