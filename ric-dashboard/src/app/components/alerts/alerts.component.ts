import { Component, OnInit } from '@angular/core';

interface Alert {
  severity: 'critical' | 'warning' | 'info';
  title: string;
  message: string;
  source: string;
  timestamp: Date;
}

@Component({
  selector: 'app-alerts',
  templateUrl: './alerts.component.html',
  styleUrls: ['./alerts.component.scss']
})
export class AlertsComponent implements OnInit {
  alerts: Alert[] = [];
  lastUpdate: Date = new Date();

  ngOnInit(): void {
    this.loadAlerts();
  }

  loadAlerts(): void {
    // Simulated alerts
    this.alerts = [
      {
        severity: 'info',
        title: 'System Information',
        message: 'All xApps are running normally',
        source: 'Platform Monitor',
        timestamp: new Date()
      }
    ];
    this.lastUpdate = new Date();
  }

  refresh(): void {
    this.loadAlerts();
  }

  getAlertIcon(severity: string): string {
    switch (severity) {
      case 'critical': return 'error';
      case 'warning': return 'warning';
      case 'info': return 'info';
      default: return 'info';
    }
  }

  getCriticalCount(): number {
    return this.alerts.filter(a => a.severity === 'critical').length;
  }

  getWarningCount(): number {
    return this.alerts.filter(a => a.severity === 'warning').length;
  }

  getInfoCount(): number {
    return this.alerts.filter(a => a.severity === 'info').length;
  }

  getHealthyCount(): number {
    // Calculate healthy systems (mock calculation)
    return this.alerts.length === 0 ? 3 : 3 - this.getCriticalCount() - this.getWarningCount();
  }
}
