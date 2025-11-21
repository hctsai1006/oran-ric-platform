import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { DashboardComponent } from './components/dashboard/dashboard.component';
import { XappsManagementComponent } from './components/xapps-management/xapps-management.component';
import { KpiMonitoringComponent } from './components/kpi-monitoring/kpi-monitoring.component';
import { GrafanaDashboardComponent } from './components/grafana-dashboard/grafana-dashboard.component';
import { DualPathMonitorComponent } from './components/dual-path-monitor/dual-path-monitor.component';
import { AlertsComponent } from './components/alerts/alerts.component';

const routes: Routes = [
  { path: '', redirectTo: '/dashboard', pathMatch: 'full' },
  { path: 'dashboard', component: DashboardComponent },
  { path: 'xapps', component: XappsManagementComponent },
  { path: 'kpi', component: KpiMonitoringComponent },
  { path: 'grafana', component: GrafanaDashboardComponent },
  { path: 'dual-path', component: DualPathMonitorComponent },
  { path: 'alerts', component: AlertsComponent },
  { path: '**', redirectTo: '/dashboard' }
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }
