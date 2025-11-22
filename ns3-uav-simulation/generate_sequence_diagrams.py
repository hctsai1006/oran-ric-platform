#!/usr/bin/env python3
"""
Generate publication-quality sequence diagrams for O-RAN UAV xApp paper.

This script creates two sequence diagrams:
1. E2 Indication Flow - Shows RSRP measurement to PRB decision flow
2. Handover Flow - Shows handover decision and execution flow

Output: PNG and PDF at 300 DPI
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np
import os

# Configure matplotlib for publication quality
plt.rcParams.update({
    'font.family': 'serif',
    'font.serif': ['Times New Roman', 'DejaVu Serif', 'serif'],
    'font.size': 10,
    'axes.labelsize': 11,
    'axes.titlesize': 12,
    'xtick.labelsize': 9,
    'ytick.labelsize': 9,
    'legend.fontsize': 9,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'text.usetex': False,
    'axes.linewidth': 0.8,
})

# Output directory
OUTPUT_DIR = '/home/thc1006/dev/oran-ric-platform/ns3-uav-simulation/results/figures'


class SequenceDiagram:
    """Class to create publication-quality sequence diagrams."""

    def __init__(self, actors, title, figsize=(12, 10)):
        """
        Initialize sequence diagram.

        Args:
            actors: List of actor names
            title: Diagram title
            figsize: Figure size in inches
        """
        self.actors = actors
        self.title = title
        self.figsize = figsize
        self.messages = []
        self.activations = []
        self.notes = []

        # Layout parameters
        self.actor_spacing = 1.8
        self.message_spacing = 0.6
        self.header_height = 0.8
        self.margin_top = 1.5
        self.margin_bottom = 0.8

        # Colors - professional academic palette
        self.colors = {
            'actor_box': '#E8E8E8',
            'actor_border': '#333333',
            'lifeline': '#666666',
            'activation': '#D0D0D0',
            'arrow': '#333333',
            'text': '#000000',
            'note_bg': '#FFFACD',
            'note_border': '#DAA520',
        }

    def add_message(self, from_actor, to_actor, label, style='solid',
                    return_msg=False, self_msg=False):
        """
        Add a message between actors.

        Args:
            from_actor: Source actor name
            to_actor: Target actor name
            label: Message label
            style: 'solid' or 'dashed'
            return_msg: If True, use open arrowhead (return message)
            self_msg: If True, message to self
        """
        self.messages.append({
            'from': from_actor,
            'to': to_actor,
            'label': label,
            'style': style,
            'return_msg': return_msg,
            'self_msg': self_msg
        })

    def add_activation(self, actor, start_msg_idx, end_msg_idx):
        """
        Add activation box for an actor.

        Args:
            actor: Actor name
            start_msg_idx: Starting message index
            end_msg_idx: Ending message index
        """
        self.activations.append({
            'actor': actor,
            'start': start_msg_idx,
            'end': end_msg_idx
        })

    def add_note(self, actor, msg_idx, text, side='right'):
        """
        Add a note near an actor at a specific message.

        Args:
            actor: Actor name
            msg_idx: Message index position
            text: Note text
            side: 'left' or 'right'
        """
        self.notes.append({
            'actor': actor,
            'msg_idx': msg_idx,
            'text': text,
            'side': side
        })

    def _get_actor_x(self, actor_name):
        """Get x-coordinate for an actor."""
        return self.actors.index(actor_name) * self.actor_spacing

    def _get_message_y(self, msg_idx):
        """Get y-coordinate for a message."""
        return -(self.margin_top + self.header_height +
                 (msg_idx + 1) * self.message_spacing)

    def draw(self, filename_base):
        """
        Draw the sequence diagram and save to files.

        Args:
            filename_base: Base filename without extension
        """
        n_messages = len(self.messages)
        fig_height = (self.margin_top + self.header_height +
                      (n_messages + 2) * self.message_spacing + self.margin_bottom)
        fig_width = (len(self.actors) - 1) * self.actor_spacing + 2.5

        fig, ax = plt.subplots(figsize=(fig_width, fig_height))

        # Set up axes
        ax.set_xlim(-1, (len(self.actors) - 1) * self.actor_spacing + 1.5)
        ax.set_ylim(-fig_height + 0.3, 0.5)
        ax.set_aspect('equal')
        ax.axis('off')

        # Draw title
        ax.text((len(self.actors) - 1) * self.actor_spacing / 2, 0.3,
                self.title, ha='center', va='bottom',
                fontsize=14, fontweight='bold', color=self.colors['text'])

        # Draw actor boxes and lifelines
        for i, actor in enumerate(self.actors):
            x = i * self.actor_spacing

            # Actor box at top
            box = FancyBboxPatch(
                (x - 0.6, -self.header_height - 0.15), 1.2, self.header_height,
                boxstyle="round,pad=0.05,rounding_size=0.1",
                facecolor=self.colors['actor_box'],
                edgecolor=self.colors['actor_border'],
                linewidth=1.2
            )
            ax.add_patch(box)

            # Actor label - handle multi-line
            lines = actor.split('\n')
            if len(lines) > 1:
                for j, line in enumerate(lines):
                    y_offset = (len(lines) - 1 - 2*j) * 0.12
                    ax.text(x, -self.header_height/2 - 0.15 + y_offset, line,
                            ha='center', va='center', fontsize=9,
                            fontweight='bold', color=self.colors['text'])
            else:
                ax.text(x, -self.header_height/2 - 0.15, actor,
                        ha='center', va='center', fontsize=9,
                        fontweight='bold', color=self.colors['text'])

            # Lifeline
            lifeline_end = self._get_message_y(n_messages) - 0.5
            ax.plot([x, x], [-self.header_height - 0.15, lifeline_end],
                    color=self.colors['lifeline'], linestyle='--',
                    linewidth=0.8, dashes=(5, 3))

            # Actor box at bottom
            box_bottom = FancyBboxPatch(
                (x - 0.6, lifeline_end - self.header_height), 1.2, self.header_height,
                boxstyle="round,pad=0.05,rounding_size=0.1",
                facecolor=self.colors['actor_box'],
                edgecolor=self.colors['actor_border'],
                linewidth=1.2
            )
            ax.add_patch(box_bottom)

            if len(lines) > 1:
                for j, line in enumerate(lines):
                    y_offset = (len(lines) - 1 - 2*j) * 0.12
                    ax.text(x, lifeline_end - self.header_height/2 + y_offset, line,
                            ha='center', va='center', fontsize=9,
                            fontweight='bold', color=self.colors['text'])
            else:
                ax.text(x, lifeline_end - self.header_height/2, actor,
                        ha='center', va='center', fontsize=9,
                        fontweight='bold', color=self.colors['text'])

        # Draw activation boxes
        for activation in self.activations:
            x = self._get_actor_x(activation['actor'])
            y_start = self._get_message_y(activation['start']) + 0.15
            y_end = self._get_message_y(activation['end']) - 0.15

            rect = mpatches.Rectangle(
                (x - 0.08, y_end), 0.16, y_start - y_end,
                facecolor=self.colors['activation'],
                edgecolor=self.colors['actor_border'],
                linewidth=0.8
            )
            ax.add_patch(rect)

        # Draw messages
        for i, msg in enumerate(self.messages):
            y = self._get_message_y(i)
            from_x = self._get_actor_x(msg['from'])
            to_x = self._get_actor_x(msg['to'])

            # Determine arrow style
            linestyle = '-' if msg['style'] == 'solid' else '--'

            if msg['self_msg']:
                # Self-message (loop back)
                loop_width = 0.4
                loop_height = 0.25

                # Draw the self-loop
                ax.annotate('', xy=(from_x + 0.08, y - loop_height),
                           xytext=(from_x + 0.08, y),
                           arrowprops=dict(arrowstyle='-', color=self.colors['arrow'],
                                          lw=1.0, linestyle=linestyle,
                                          connectionstyle=f'arc3,rad=-0.5'))
                ax.plot([from_x + 0.08, from_x + loop_width], [y, y],
                       color=self.colors['arrow'], linewidth=1.0, linestyle=linestyle)
                ax.plot([from_x + loop_width, from_x + loop_width], [y, y - loop_height],
                       color=self.colors['arrow'], linewidth=1.0, linestyle=linestyle)
                ax.annotate('', xy=(from_x + 0.08, y - loop_height),
                           xytext=(from_x + loop_width, y - loop_height),
                           arrowprops=dict(arrowstyle='->', color=self.colors['arrow'],
                                          lw=1.0))

                # Label
                ax.text(from_x + loop_width + 0.1, y - loop_height/2, msg['label'],
                       ha='left', va='center', fontsize=8,
                       color=self.colors['text'])
            else:
                # Regular message
                direction = 1 if to_x > from_x else -1

                # Adjust for activation boxes
                from_x_adj = from_x + direction * 0.08
                to_x_adj = to_x - direction * 0.08

                # Arrow style
                if msg['return_msg']:
                    arrowstyle = '->'
                    head_width = 0.08
                    head_length = 0.06
                else:
                    arrowstyle = '->'
                    head_width = 0.1
                    head_length = 0.08

                # Draw arrow
                ax.annotate('', xy=(to_x_adj, y), xytext=(from_x_adj, y),
                           arrowprops=dict(arrowstyle=arrowstyle,
                                          color=self.colors['arrow'],
                                          lw=1.2,
                                          linestyle=linestyle,
                                          shrinkA=0, shrinkB=0))

                # Label - position above the arrow
                mid_x = (from_x_adj + to_x_adj) / 2
                ax.text(mid_x, y + 0.12, msg['label'],
                       ha='center', va='bottom', fontsize=8,
                       color=self.colors['text'])

        # Draw notes
        for note in self.notes:
            x = self._get_actor_x(note['actor'])
            y = self._get_message_y(note['msg_idx'])

            if note['side'] == 'right':
                note_x = x + 0.5
                ha = 'left'
            else:
                note_x = x - 0.5
                ha = 'right'

            # Note box
            note_box = FancyBboxPatch(
                (note_x - 0.4 if ha == 'right' else note_x, y - 0.15),
                0.8, 0.3,
                boxstyle="round,pad=0.02",
                facecolor=self.colors['note_bg'],
                edgecolor=self.colors['note_border'],
                linewidth=0.8
            )
            ax.add_patch(note_box)
            ax.text(note_x + (0.4 if ha == 'left' else -0.4), y,
                   note['text'], ha='center', va='center', fontsize=7,
                   color=self.colors['text'], style='italic')

        plt.tight_layout()

        # Save files
        png_path = os.path.join(OUTPUT_DIR, f'{filename_base}.png')
        pdf_path = os.path.join(OUTPUT_DIR, f'{filename_base}.pdf')

        fig.savefig(png_path, dpi=300, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        fig.savefig(pdf_path, dpi=300, bbox_inches='tight',
                   facecolor='white', edgecolor='none')

        plt.close(fig)

        print(f"Saved: {png_path}")
        print(f"Saved: {pdf_path}")

        return png_path, pdf_path


def create_e2_indication_diagram():
    """Create E2 Indication Flow sequence diagram."""

    actors = ['UAV UE', 'eNB', 'E2 Node', 'Near-RT\nRIC', 'UAV Policy\nxApp', 'SDL']

    diagram = SequenceDiagram(
        actors=actors,
        title='E2 Indication Flow: RSRP Measurement to PRB Allocation'
    )

    # Message sequence
    # 1. RSRP measurement
    diagram.add_message('UAV UE', 'eNB', '1. RSRP Measurement Report')

    # 2. eNB to E2 Node
    diagram.add_message('eNB', 'E2 Node', '2. RAN Metrics (RSRP, CQI)')

    # 3. E2 Indication to RIC
    diagram.add_message('E2 Node', 'Near-RT\nRIC', '3. E2 Indication Message')

    # 4. RIC to xApp
    diagram.add_message('Near-RT\nRIC', 'UAV Policy\nxApp', '4. RMR Indication (msg_type=12050)')

    # 5. xApp queries SDL for context
    diagram.add_message('UAV Policy\nxApp', 'SDL', '5. GET UE Context')

    # 6. SDL returns data
    diagram.add_message('SDL', 'UAV Policy\nxApp', '6. UE Context Data', return_msg=True)

    # 7. xApp processes (self message)
    diagram.add_message('UAV Policy\nxApp', 'UAV Policy\nxApp', '7. Process KPM', self_msg=True)

    # 8. xApp stores decision
    diagram.add_message('UAV Policy\nxApp', 'SDL', '8. Store PRB Decision')

    # 9. xApp sends control to RIC
    diagram.add_message('UAV Policy\nxApp', 'Near-RT\nRIC', '9. RMR Control (msg_type=12040)')

    # 10. RIC to E2 Node
    diagram.add_message('Near-RT\nRIC', 'E2 Node', '10. E2 Control Request')

    # 11. E2 Node to eNB
    diagram.add_message('E2 Node', 'eNB', '11. PRB Allocation Command')

    # 12. eNB applies
    diagram.add_message('eNB', 'UAV UE', '12. Resource Grant (PRB)', return_msg=True)

    # Add activations
    diagram.add_activation('UAV UE', 0, 0)
    diagram.add_activation('eNB', 0, 11)
    diagram.add_activation('E2 Node', 1, 10)
    diagram.add_activation('Near-RT\nRIC', 2, 9)
    diagram.add_activation('UAV Policy\nxApp', 3, 8)
    diagram.add_activation('SDL', 4, 7)

    return diagram.draw('e2_indication_sequence')


def create_handover_diagram():
    """Create Handover Flow sequence diagram."""

    actors = ['UAV UE', 'Source\neNB', 'Target\neNB', 'Near-RT\nRIC', 'UAV Policy\nxApp']

    diagram = SequenceDiagram(
        actors=actors,
        title='Handover Flow: Measurement-Triggered Handover with PRB Pre-allocation'
    )

    # Message sequence
    # 1. UE sends measurement report
    diagram.add_message('UAV UE', 'Source\neNB', '1. Measurement Report (A3 Event)')

    # 2. Source eNB reports to RIC
    diagram.add_message('Source\neNB', 'Near-RT\nRIC', '2. E2 Indication (Handover Trigger)')

    # 3. RIC forwards to xApp
    diagram.add_message('Near-RT\nRIC', 'UAV Policy\nxApp', '3. RMR HO Request')

    # 4. xApp processes handover decision
    diagram.add_message('UAV Policy\nxApp', 'UAV Policy\nxApp', '4. Evaluate HO Decision', self_msg=True)

    # 5. xApp sends PRB pre-allocation to target
    diagram.add_message('UAV Policy\nxApp', 'Near-RT\nRIC', '5. PRB Pre-alloc Request')

    # 6. RIC to Target eNB
    diagram.add_message('Near-RT\nRIC', 'Target\neNB', '6. E2 Control (PRB Reserve)')

    # 7. Target confirms
    diagram.add_message('Target\neNB', 'Near-RT\nRIC', '7. PRB Reserve ACK', return_msg=True)

    # 8. RIC to xApp
    diagram.add_message('Near-RT\nRIC', 'UAV Policy\nxApp', '8. Reserve Confirmed', return_msg=True)

    # 9. xApp initiates handover
    diagram.add_message('UAV Policy\nxApp', 'Near-RT\nRIC', '9. Execute Handover')

    # 10. RIC commands source
    diagram.add_message('Near-RT\nRIC', 'Source\neNB', '10. HO Command')

    # 11. X2 Handover Request
    diagram.add_message('Source\neNB', 'Target\neNB', '11. X2: HO Request')

    # 12. X2 Handover ACK
    diagram.add_message('Target\neNB', 'Source\neNB', '12. X2: HO Request ACK', return_msg=True)

    # 13. RRC Reconfiguration
    diagram.add_message('Source\neNB', 'UAV UE', '13. RRC Connection Reconfiguration')

    # 14. UE connects to target
    diagram.add_message('UAV UE', 'Target\neNB', '14. RRC Reconfig Complete')

    # 15. Target confirms to RIC
    diagram.add_message('Target\neNB', 'Near-RT\nRIC', '15. HO Complete Indication')

    # 16. RIC notifies xApp
    diagram.add_message('Near-RT\nRIC', 'UAV Policy\nxApp', '16. HO Complete', return_msg=True)

    # Add activations
    diagram.add_activation('UAV UE', 0, 13)
    diagram.add_activation('Source\neNB', 0, 12)
    diagram.add_activation('Target\neNB', 5, 15)
    diagram.add_activation('Near-RT\nRIC', 1, 15)
    diagram.add_activation('UAV Policy\nxApp', 2, 16)

    return diagram.draw('handover_sequence')


def main():
    """Generate all sequence diagrams."""

    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 60)
    print("Generating O-RAN UAV xApp Sequence Diagrams")
    print("=" * 60)

    # Generate E2 Indication Flow diagram
    print("\n[1/2] Generating E2 Indication Flow diagram...")
    e2_png, e2_pdf = create_e2_indication_diagram()

    # Generate Handover Flow diagram
    print("\n[2/2] Generating Handover Flow diagram...")
    ho_png, ho_pdf = create_handover_diagram()

    print("\n" + "=" * 60)
    print("Generation complete!")
    print("=" * 60)
    print(f"\nOutput directory: {OUTPUT_DIR}")
    print("\nGenerated files:")
    print(f"  - E2 Indication: {os.path.basename(e2_png)}, {os.path.basename(e2_pdf)}")
    print(f"  - Handover Flow: {os.path.basename(ho_png)}, {os.path.basename(ho_pdf)}")


if __name__ == '__main__':
    main()
