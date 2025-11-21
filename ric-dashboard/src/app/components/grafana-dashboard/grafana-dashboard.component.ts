import { Component, OnInit, OnDestroy } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { interval, Subscription } from 'rxjs';
import { switchMap } from 'rxjs/operators';

interface ClusterStats {
  nodes: number;
  pods: number;
  services: number;
  deployments: number;
}

@Component({
  selector: 'app-grafana-dashboard',
  templateUrl: './grafana-dashboard.component.html',
  styleUrl: './grafana-dashboard.component.scss'
})
export class GrafanaDashboardComponent implements OnInit, OnDestroy {
  grafanaUrl: SafeResourceUrl;
  clusterStats: ClusterStats = {
    nodes: 0,
    pods: 0,
    services: 0,
    deployments: 0
  };

  private refreshSubscription?: Subscription;

  constructor(
    private http: HttpClient,
    private sanitizer: DomSanitizer
  ) {
    // Sanitize Grafana URL for iframe embedding (using nginx proxy)
    this.grafanaUrl = this.sanitizer.bypassSecurityTrustResourceUrl('/grafana/');
  }

  ngOnInit(): void {
    this.loadClusterStats();

    // Refresh every 10 seconds
    this.refreshSubscription = interval(10000)
      .pipe(switchMap(() => this.http.get<ClusterStats>('/api/cluster/stats')))
      .subscribe({
        next: (stats) => this.clusterStats = stats,
        error: (err) => console.error('Error loading cluster stats:', err)
      });
  }

  ngOnDestroy(): void {
    this.refreshSubscription?.unsubscribe();
  }

  loadClusterStats(): void {
    this.http.get<ClusterStats>('/api/cluster/stats').subscribe({
      next: (stats) => this.clusterStats = stats,
      error: (err) => console.error('Error loading cluster stats:', err)
    });
  }

  openGrafana(): void {
    // Open Grafana in a new window using proxy
    const grafanaUrl = '/grafana/';
    window.open(grafanaUrl, '_blank');
  }
}
