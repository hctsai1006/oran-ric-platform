import { Component, OnInit, OnDestroy } from '@angular/core';
import { XappService, XApp } from '../../services/xapp.service';
import { PrometheusService } from '../../services/prometheus.service';
import { interval, Subscription } from 'rxjs';
import { switchMap } from 'rxjs/operators';

interface PlatformStats {
  totalXApps: number;
  healthyXApps: number;
  totalReplicas: number;
  readyReplicas: number;
  uptime: string;
}

@Component({
  selector: 'app-dashboard',
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.scss']
})
export class DashboardComponent implements OnInit, OnDestroy {
  xapps: XApp[] = [];
  stats: PlatformStats = {
    totalXApps: 0,
    healthyXApps: 0,
    totalReplicas: 0,
    readyReplicas: 0,
    uptime: '0h 0m'
  };
  loading = true;
  error: string | null = null;
  private refreshSubscription?: Subscription;

  displayedColumns: string[] = ['name', 'status', 'replicas', 'version', 'health'];

  constructor(
    private xappService: XappService,
    private prometheusService: PrometheusService
  ) {}

  ngOnInit(): void {
    this.loadData();
    // Refresh every 10 seconds
    this.refreshSubscription = interval(10000)
      .pipe(switchMap(() => this.xappService.getXApps()))
      .subscribe({
        next: (xapps) => {
          this.xapps = xapps;
          this.updateStats();
        },
        error: (err) => console.error('Error refreshing xApps:', err)
      });
  }

  ngOnDestroy(): void {
    if (this.refreshSubscription) {
      this.refreshSubscription.unsubscribe();
    }
  }

  loadData(): void {
    this.loading = true;
    this.error = null;

    this.xappService.getXApps().subscribe({
      next: (xapps) => {
        this.xapps = xapps;
        this.updateStats();
        this.loading = false;
      },
      error: (err) => {
        this.error = 'Failed to load xApps: ' + err.message;
        this.loading = false;
      }
    });
  }

  updateStats(): void {
    this.stats.totalXApps = this.xapps.length;
    this.stats.healthyXApps = this.xapps.filter(x => x.status === 'Running').length;
    this.stats.totalReplicas = this.xapps.reduce((sum, x) => sum + x.replicas, 0);
    this.stats.readyReplicas = this.xapps.reduce((sum, x) => sum + x.ready_replicas, 0);
    // Calculate uptime (placeholder - you can add real uptime calculation)
    this.stats.uptime = '0h 0m';
  }

  getStatusColor(status: string): string {
    switch (status) {
      case 'Running': return 'primary';
      case 'Degraded': return 'warn';
      default: return 'accent';
    }
  }

  getHealthIcon(health: any): string {
    if (health.alive && health.ready) return 'check_circle';
    if (health.alive) return 'warning';
    return 'error';
  }

  getHealthColor(health: any): string {
    if (health.alive && health.ready) return 'green';
    if (health.alive) return 'orange';
    return 'red';
  }

  refresh(): void {
    this.loadData();
  }
}
