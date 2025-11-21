import { Component, OnInit, OnDestroy } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { interval, Subscription } from 'rxjs';
import { switchMap } from 'rxjs/operators';

interface NetworkNode {
  id: string;
  label: string;
  x: number;
  y: number;
  type: 'platform' | 'xapp' | 'e2node';
  status: 'healthy' | 'warning' | 'error';
}

interface NetworkLink {
  source: string;
  target: string;
  type: 'rmr' | 'http';
  status: 'active' | 'inactive' | 'degraded';
  latency?: number;
}

interface PathMetrics {
  rmr: {
    status: string;
    messagesPerSec: number;
    avgLatency: number;
    errorRate: number;
  };
  http: {
    status: string;
    requestsPerSec: number;
    avgLatency: number;
    errorRate: number;
  };
}

@Component({
  selector: 'app-dual-path-monitor',
  templateUrl: './dual-path-monitor.component.html',
  styleUrl: './dual-path-monitor.component.scss'
})
export class DualPathMonitorComponent implements OnInit, OnDestroy {
  nodes: NetworkNode[] = [
    { id: 'ric-platform', label: 'RIC Platform', x: 400, y: 100, type: 'platform', status: 'healthy' },
    { id: 'xapp-kpimon', label: 'KPI Monitor xApp', x: 200, y: 250, type: 'xapp', status: 'healthy' },
    { id: 'xapp-hw', label: 'HelloWorld xApp', x: 400, y: 250, type: 'xapp', status: 'healthy' },
    { id: 'xapp-ts', label: 'TrafficSteering xApp', x: 600, y: 250, type: 'xapp', status: 'healthy' },
    { id: 'e2node-1', label: 'E2 Node 1', x: 200, y: 400, type: 'e2node', status: 'healthy' },
    { id: 'e2node-2', label: 'E2 Node 2', x: 400, y: 400, type: 'e2node', status: 'healthy' },
    { id: 'e2node-3', label: 'E2 Node 3', x: 600, y: 400, type: 'e2node', status: 'healthy' }
  ];

  links: NetworkLink[] = [
    // RMR paths (primary communication)
    { source: 'ric-platform', target: 'xapp-kpimon', type: 'rmr', status: 'active', latency: 2.3 },
    { source: 'ric-platform', target: 'xapp-hw', type: 'rmr', status: 'active', latency: 1.8 },
    { source: 'ric-platform', target: 'xapp-ts', type: 'rmr', status: 'active', latency: 2.1 },
    { source: 'xapp-kpimon', target: 'e2node-1', type: 'rmr', status: 'active', latency: 3.5 },
    { source: 'xapp-hw', target: 'e2node-2', type: 'rmr', status: 'active', latency: 3.2 },
    { source: 'xapp-ts', target: 'e2node-3', type: 'rmr', status: 'active', latency: 3.8 },

    // HTTP paths (backup/monitoring)
    { source: 'ric-platform', target: 'xapp-kpimon', type: 'http', status: 'active', latency: 5.2 },
    { source: 'ric-platform', target: 'xapp-hw', type: 'http', status: 'active', latency: 4.8 },
    { source: 'ric-platform', target: 'xapp-ts', type: 'http', status: 'active', latency: 5.1 }
  ];

  pathMetrics: PathMetrics = {
    rmr: {
      status: 'Operational',
      messagesPerSec: 1247,
      avgLatency: 2.8,
      errorRate: 0.02
    },
    http: {
      status: 'Operational',
      requestsPerSec: 156,
      avgLatency: 5.1,
      errorRate: 0.01
    }
  };

  private refreshSubscription?: Subscription;

  constructor(private http: HttpClient) {}

  ngOnInit(): void {
    this.loadPathMetrics();

    // Refresh metrics every 5 seconds
    this.refreshSubscription = interval(5000)
      .pipe(switchMap(() => this.http.get<PathMetrics>('/api/dual-path/metrics')))
      .subscribe({
        next: (metrics) => this.pathMetrics = metrics,
        error: (err) => console.log('Using mock data for dual-path metrics')
      });
  }

  ngOnDestroy(): void {
    this.refreshSubscription?.unsubscribe();
  }

  loadPathMetrics(): void {
    this.http.get<PathMetrics>('/api/dual-path/metrics').subscribe({
      next: (metrics) => this.pathMetrics = metrics,
      error: (err) => console.log('Using mock data for dual-path metrics')
    });
  }

  getNodeColor(node: NetworkNode): string {
    switch (node.type) {
      case 'platform': return '#1976d2';
      case 'xapp': return '#43a047';
      case 'e2node': return '#f57c00';
      default: return '#757575';
    }
  }

  getNodePosition(nodeId: string): { x: number; y: number } {
    const node = this.nodes.find(n => n.id === nodeId);
    return node ? { x: node.x, y: node.y } : { x: 0, y: 0 };
  }

  getLinkPath(link: NetworkLink): string {
    const source = this.getNodePosition(link.source);
    const target = this.getNodePosition(link.target);

    // Offset for dual paths (RMR and HTTP side by side)
    const offset = link.type === 'rmr' ? -3 : 3;
    const dx = target.x - source.x;
    const dy = target.y - source.y;
    const dist = Math.sqrt(dx * dx + dy * dy);
    const offsetX = (-dy / dist) * offset;
    const offsetY = (dx / dist) * offset;

    return `M ${source.x + offsetX} ${source.y + offsetY} L ${target.x + offsetX} ${target.y + offsetY}`;
  }

  getLinkColor(link: NetworkLink): string {
    if (link.status === 'inactive') return '#bdbdbd';
    if (link.status === 'degraded') return '#ff9800';
    return link.type === 'rmr' ? '#2196f3' : '#4caf50';
  }

  getStatusColor(status: string): string {
    if (status === 'Operational') return '#4caf50';
    if (status === 'Degraded') return '#ff9800';
    return '#f44336';
  }
}
